import pathlib
import asyncio
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

                CONSOLE.log(
                    f"Sending HTTP {probe.method} to {probe.url} (expecting {probe.expected_status_code})"
                )
                async with httpx.AsyncClient() as client:
                    with metrics.http_response_duration_histogram.labels(
                        method=probe.method, url=probe.url
                    ).time():
                        response = await client.request(
                            method=probe.method, url=probe.url
                        )
                    CONSOLE.log(
                        f"Got {response.status_code} from HTTP {probe.method} to {probe.url} (expected {probe.expected_status_code})"
                    )
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
                CONSOLE.log(f"Sending ICMP packet to {probe.hostname}")
                metrics.icmp_request_count.labels(hostname=probe.hostname).inc()
                with metrics.icmp_response_duration_histogram.labels(
                    hostname=probe.hostname
                ).time():
                    ping_host = await async_ping(address=probe.hostname, count=1)
                CONSOLE.log(
                    f"Got ICMP response from {probe.hostname}: RTT: {ping_host.max_rtt} Alive?: {ping_host.is_alive}"
                )
                success = ping_host.is_alive
                max_rtt = ping_host.max_rtt / 1000  # ms to seconds
                metrics.icmp_response_count.labels(
                    hostname=probe.hostname, success=success
                ).inc()
                metrics.icmp_max_rtt_histogram.labels(hostname=probe.hostname).observe(
                    max_rtt
                )
                metrics.probe_finished_count.labels(
                    success=success, protocol=probe.protocol
                ).inc()
            case _:
                raise NotImplementedError(probe)


async def go(probes_config_path: pathlib.Path):
    previous_stat = None
    probes_config = None
    while True:
        stat = probes_config_path.stat()
        new_stat = (stat.st_size, stat.st_mtime)
        if probes_config is None or previous_stat != new_stat:
            CONSOLE.log(f"(re-)loading probes config from {probes_config_path}")
            probes_config = parse_yaml_file_as(ProbesConfig, probes_config_path)
            previous_stat = new_stat
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
