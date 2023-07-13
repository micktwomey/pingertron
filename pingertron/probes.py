import asyncio
import random

import httpx
import structlog
from icmplib import async_ping

from . import metrics
from .probes_config import FailingProbe, FailureMode, HTTPProbe, ICMPProbe, Probe


async def run_probe(
    config: Probe,
    # TODO: Add timeouts
    # TODO: Yield events from the probe or return a result to feed the logs and metrics
):
    logger_kwargs = config.dict()
    log: structlog.stdlib.BoundLogger = structlog.get_logger(**logger_kwargs)
    try:
        log.debug("ping")
        match config:
            case HTTPProbe():
                success = await do_http_probe(config, log)
            case ICMPProbe():
                success = await do_icmp_probe(config, log)
            case FailingProbe():
                success = await do_failing_probe(config, log)
            case _:
                raise NotImplementedError(config)
        if success:
            log.debug("ack")
        else:
            log.debug("no-ack")
        metrics.probe_finished_count.labels(
            success=success, protocol=config.protocol
        ).inc()
    except Exception:
        log.exception("exception")
        metrics.probe_finished_count.labels(
            success=False, protocol=config.protocol
        ).inc()


async def do_http_probe(probe: HTTPProbe, log: structlog.stdlib.BoundLogger) -> bool:
    metrics.http_request_count.labels(
        method=probe.method,
        url=probe.url,
        expected_status_code=probe.expected_status_code,
    ).inc()

    async with httpx.AsyncClient() as client:
        with metrics.http_response_duration_histogram.labels(
            method=probe.method, url=probe.url
        ).time():
            response = await client.request(method=probe.method, url=probe.url)
        success = response.status_code == probe.expected_status_code
        metrics.http_response_count.labels(
            method=probe.method,
            url=probe.url,
            expected_status_code=probe.expected_status_code,
            status_code=response.status_code,
            success=success,
        ).inc()
    return success


async def do_icmp_probe(probe: ICMPProbe, log: structlog.stdlib.BoundLogger) -> bool:
    metrics.icmp_request_count.labels(hostname=probe.hostname).inc()
    with metrics.icmp_response_duration_histogram.labels(
        hostname=probe.hostname
    ).time():
        ping_host = await async_ping(address=probe.hostname, count=1)
    success = ping_host.is_alive
    max_rtt = ping_host.max_rtt / 1000  # ms to seconds
    metrics.icmp_response_count.labels(hostname=probe.hostname, success=success).inc()
    metrics.icmp_max_rtt_histogram.labels(hostname=probe.hostname).observe(max_rtt)
    return success


class Failure(Exception):
    """Raised by failing probe"""


async def do_failing_probe(
    probe: FailingProbe, log: structlog.stdlib.BoundLogger
) -> bool:
    if random.random() <= probe.failure_rate:
        match probe.failure_mode:
            case FailureMode.exception:
                raise Failure("Oh no!")
            case FailureMode.timeout:
                while True:
                    await asyncio.sleep(1e9)  # sleep for a very long time
    return True
