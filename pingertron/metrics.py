import prometheus_client
from opentelemetry import metrics, trace
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

resource = Resource(attributes={SERVICE_NAME: "pingertron"})

meter = metrics.get_meter("pingertron.meter")

http_request_count = meter.create_counter(
    "http_request_count",
    description="The number of HTTP requests started",
)

http_response_count = meter.create_counter(
    "http_response_count", description="The number of HTTP responses received"
)

http_response_duration_histogram = meter.create_histogram(
    "http_response_duration_histogram",
    unit="s",
    description="Histogram of HTTP response durations (seconds)",
)

probe_finished_count = meter.create_counter(
    "probe_finished_count", description="Count of probe results (success or failed)"
)

icmp_request_count = meter.create_counter(
    "icmp_request_count",
    description="The number of ICMP requests started",
)

icmp_response_count = meter.create_counter(
    "icmp_response_count", description="The number of ICMP responses received"
)

icmp_response_duration_histogram = meter.create_histogram(
    "icmp_response_duration_histogram",
    unit="s",
    description="Histogram of ICMP response durations (seconds)",
)


def setup_metrics(prometheus_exporter_port: int):
    """Call once at beginning of program to setup your metrics"""
    HTTPXClientInstrumentor().instrument()

    prometheus_client.start_http_server(prometheus_exporter_port)

    reader = PrometheusMetricReader()
    provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(provider)

    provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
