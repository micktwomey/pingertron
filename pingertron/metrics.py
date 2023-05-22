import prometheus_client
from prometheus_client import Counter, Histogram

http_request_count = Counter(
    "http_request_count",
    "The number of HTTP requests started",
    labelnames=["method", "url", "expected_status_code"],
)

http_response_count = Counter(
    "http_response_count",
    "The number of HTTP responses received",
    labelnames=["method", "url", "expected_status_code", "status_code", "success"],
)

http_response_duration_histogram = Histogram(
    "http_response_duration_histogram",
    "Histogram of HTTP response durations (seconds)",
    unit="seconds",
    labelnames=["method", "url"],
)

probe_finished_count = Counter(
    "probe_finished_count",
    "Count of probe results (success or failed)",
    labelnames=["success", "protocol"],
)

icmp_request_count = Counter(
    "icmp_request_count",
    "The number of ICMP requests started",
    labelnames=["hostname"],
)

icmp_response_count = Counter(
    "icmp_response_count",
    "The number of ICMP responses received",
    labelnames=["hostname", "success"],
)

icmp_response_duration_histogram = Histogram(
    "icmp_response_duration_histogram",
    "Summary of ICMP response durations (seconds)",
    unit="seconds",
    labelnames=["hostname"],
)

icmp_max_rtt_histogram = Histogram(
    "icmp_max_rtt_histogram",
    "Summary of ICMP response max rtt (seconds)",
    unit="seconds",
    labelnames=["hostname"],
)


def setup_metrics(prometheus_exporter_port: int):
    """Call once at beginning of program to setup your metrics"""

    prometheus_client.start_http_server(prometheus_exporter_port)
