import enum
import asyncio
from typing import Annotated

import httpx
import prometheus_client
import pydantic
from pydantic_yaml import parse_yaml_file_as
import rich.console
import rich.traceback
import typer
from opentelemetry import metrics, trace
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from .probes_config import ProbesConfig, Probe, ICMPProbe, HTTPProbe

CONSOLE = rich.console.Console()

resource = Resource(attributes={SERVICE_NAME: "pingertron"})
meter = metrics.get_meter("pingertron.meter")
request_count = meter.create_counter(
    "request_count",
    description="The number of requests started",
)

async def run_probes(probes: list[Probe]):
    for probe in probes:
        match probe:
            case HTTPProbe() as probe:
                CONSOLE.log("HTTP", probe)
            case ICMPProbe() as probe:
                CONSOLE.log("ICMP", probe)
            case _:
                raise NotImplementedError(probe)


async def go(probes_config: ProbesConfig):
    while True:
        await run_probes(probes_config.probes)
        await asyncio.sleep(probes_config.interval_seconds)





def main(config: Annotated[typer.FileText, typer.Argument()], prometheus_exporter_port: int = 8000, ):
    rich.traceback.install(show_locals=True)
    HTTPXClientInstrumentor().instrument()

    probes_config = parse_yaml_file_as(ProbesConfig, config)
    CONSOLE.log(probes_config)

    prometheus_client.start_http_server(prometheus_exporter_port)

    reader = PrometheusMetricReader()
    provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(provider)

    provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    asyncio.run(go(probes_config=probes_config))


if __name__ == "__main__":
    typer.run(main)
