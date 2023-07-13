import asyncio
import logging
import pathlib
from typing import Annotated

import rich.traceback
import structlog
import structlog.contextvars
import structlog.processors
import typer
from pydantic_yaml import parse_yaml_file_as

from . import metrics
from .probes import run_probe
from .probes_config import Probe, ProbesConfig

app = typer.Typer()

LOG: structlog.stdlib.BoundLogger = structlog.get_logger()


async def run_probes(probes: list[Probe]):
    # TODO: add a timeout of max(5, interval - 5)
    # (minimum 5 seconds and timeout before next loop)
    async with asyncio.TaskGroup() as group:
        for probe in probes:
            group.create_task(run_probe(probe))


async def go(probes_config_path: pathlib.Path):
    previous_stat = None
    probes_config = None
    while True:
        stat = probes_config_path.stat()
        new_stat = (stat.st_size, stat.st_mtime)
        if probes_config is None or previous_stat != new_stat:
            LOG.debug("Loading probes config", config_path=probes_config_path)
            probes_config = parse_yaml_file_as(ProbesConfig, probes_config_path)
            previous_stat = new_stat
            LOG.info("Loaded probes config", config=probes_config.dict())

        # Start the sleep at the same time as the probes, aiming to start next batch of
        # probes close to exactly the interval time.
        async with asyncio.TaskGroup() as group:
            group.create_task(run_probes(probes_config.probes))
            group.create_task(asyncio.sleep(probes_config.interval_seconds))


@app.command()
def main(
    config: Annotated[pathlib.Path, typer.Argument(help="Path to probes.yml config")],
    prometheus_exporter_port: Annotated[
        int, typer.Option(help="Port to export prometheus metrics on")
    ] = 8000,
    use_json_logging: Annotated[
        bool, typer.Option(help="Output using JSON logging?")
    ] = False,
    verbose: Annotated[bool, typer.Option(help="More verbose log output?")] = False,
):
    rich.traceback.install(show_locals=True)
    log_level = logging.DEBUG if verbose else logging.INFO
    if use_json_logging:
        # Configure same processor stack as default, minus dev bits
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.StackInfoRenderer(),
                structlog.processors.TimeStamper(fmt="iso", utc=True),
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(log_level),
        )
    else:
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(log_level),
        )

    metrics.setup_metrics(prometheus_exporter_port=prometheus_exporter_port)
    LOG.debug(f"Prometheus metrics available on port {prometheus_exporter_port}")

    asyncio.run(go(probes_config_path=config))


if __name__ == "__main__":
    typer.run(app)
