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
                metrics.http_request_count.add(
                    1,
                    {
                        "http.method": probe.method,
                        "http.url": probe.url,
                        "http.expected_status_code": probe.expected_status_code,
                    },
                )
                CONSOLE.log("HTTP", probe)
                async with httpx.AsyncClient() as client:
                    start = time.monotonic()
                    response = await client.request(method=probe.method, url=probe.url)
                    end = time.monotonic()
                    duration = end - start
                    CONSOLE.log("HTTP Response", response)
                    success = response.status_code == probe.expected_status_code
                    metrics.http_response_count.add(
                        1,
                        {
                            "http.method": probe.method,
                            "http.url": probe.url,
                            "http.status_code": response.status_code,
                            "success": success,
                        },
                    )
                    metrics.http_response_duration_histogram.record(
                        duration,
                        {
                            "http.method": probe.method,
                            "http.url": probe.url,
                            "http.status_code": response.status_code,
                            "success": response.status_code
                            == probe.expected_status_code,
                        },
                    )
                    metrics.probe_finished_count.add(
                        1,
                        {
                            "success": success,
                            "protocol": probe.protocol,
                        },
                    )
            case ICMPProbe():
                metrics.icmp_request_count.add(
                    1,
                    {
                        "icmp.hostname": probe.hostname,
                    },
                )
                ping_host = await async_ping(address=probe.hostname, count=1)
                success = ping_host.is_alive
                duration = ping_host.max_rtt / 1000  # ms to seconds
                CONSOLE.log("ICMP", probe)
                metrics.icmp_response_count.add(
                    1,
                    {
                        "hostname": probe.hostname,
                        "success": success,
                    },
                )
                metrics.icmp_response_duration_histogram.record(
                    duration,
                    {
                        "hostname": probe.hostname,
                        "success": success,
                    },
                )
                metrics.probe_finished_count.add(
                    1,
                    {
                        "success": success,
                        "protocol": probe.protocol,
                    },
                )
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
