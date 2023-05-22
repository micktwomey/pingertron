import enum

import pydantic


class Protocol(enum.StrEnum):
    http = "http"
    icmp = "icmp"


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


Probe = HTTPProbe | ICMPProbe


class ProbesConfig(pydantic.BaseModel):
    interval_seconds: float = 60
    probes: list[Probe]
