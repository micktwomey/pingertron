import enum

import pydantic


class Protocol(enum.StrEnum):
    http = "http"
    icmp = "icmp"
    failing = "failing"


class HTTPProbe(pydantic.BaseModel):
    protocol: Protocol = Protocol.http
    description: str | None
    url: str
    method: str = "GET"
    expected_status_code: int = 200


class ICMPProbe(pydantic.BaseModel):
    protocol: Protocol = Protocol.icmp
    description: str | None
    hostname: str


class FailureMode(enum.StrEnum):
    exception = "exception"
    timeout = "timeout"


class FailingProbe(pydantic.BaseModel):
    protocol: Protocol = Protocol.failing
    description: str | None
    failure_rate: float = 0.8
    failure_mode: FailureMode


Probe = HTTPProbe | ICMPProbe | FailingProbe


class ProbesConfig(pydantic.BaseModel):
    interval_seconds: float = 60
    probes: list[Probe]
