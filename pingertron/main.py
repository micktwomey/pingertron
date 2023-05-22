import pathlib
import asyncio
import time
from typing import Annotated

import httpx
from icmplib import async_ping
from pydantic_yaml import parse_yaml_file_as
import rich.console
import rich.traceback
import typer

from . import metrics
from .probes_config import ProbesConfig, Probe, ICMPProbe, HTTPProbe

app = typer.Typer()

CONSOLE = rich.console.Console()


async def run_probes(probes: list[Probe]):
    # TODO: dispatch these in parallel
    for probe in probes:
        match probe:
            case HTTPProbe():
                metrics.http_request_count.labels(
                    method=probe.method,
                    url=probe.url,
                    expected_status_code=probe.expected_status_code,
                ).inc()

                CONSOLE.log("HTTP", probe)
                async with httpx.AsyncClient() as client:
                    with metrics.http_response_duration_summary.labels(
                        method=probe.method, url=probe.url
                    ).time():
                        response = await client.request(
                            method=probe.method, url=probe.url
                        )
                    CONSOLE.log("HTTP Response", response)
                    success = response.status_code == probe.expected_status_code
                    metrics.http_response_count.labels(
                        method=probe.method,
                        url=probe.url,
                        expected_status_code=probe.expected_status_code,
                        status_code=response.status_code,
                        success=success,
                    ).inc()
                    metrics.probe_finished_count.labels(
                        success=success, protocol=probe.protocol
                    ).inc()
            case ICMPProbe():
                metrics.icmp_request_count.labels(hostname=probe.hostname).inc()
                with metrics.icmp_response_duration_summary.labels(
                    hostname=probe.hostname
                ).time():
                    ping_host = await async_ping(address=probe.hostname, count=1)
                success = ping_host.is_alive
                max_rtt = ping_host.max_rtt / 1000  # ms to seconds
                CONSOLE.log("ICMP", probe)
                metrics.icmp_response_count.labels(
                    hostname=probe.hostname, success=success
                ).inc()
                metrics.icmp_max_rtt_summary.labels(hostname=probe.hostname).observe(
                    max_rtt
                )
                metrics.probe_finished_count.labels(
                    success=success, protocol=probe.protocol
                ).inc()
            case _:
                raise NotImplementedError(probe)


async def go(probes_config_path: pathlib.Path):
    while True:
        probes_config = parse_yaml_file_as(ProbesConfig, probes_config_path)
        CONSOLE.log(probes_config)
        await run_probes(probes_config.probes)
        await asyncio.sleep(probes_config.interval_seconds)


@app.command()
def main(
    config: Annotated[pathlib.Path, typer.Argument()],
    prometheus_exporter_port: int = 8000,
):
    rich.traceback.install(show_locals=True)
    metrics.setup_metrics(prometheus_exporter_port=prometheus_exporter_port)

    asyncio.run(go(probes_config_path=config))


if __name__ == "__main__":
    typer.run(app)
