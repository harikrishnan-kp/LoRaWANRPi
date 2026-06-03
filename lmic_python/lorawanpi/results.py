from __future__ import annotations

from dataclasses import dataclass, field

from .config import ActivationMode


@dataclass(frozen=True)
class RadioMetadata:
    rssi_dbm: int | None = None
    snr_db: float | None = None


@dataclass(frozen=True)
class Downlink:
    payload: bytes
    port: int | None = None
    radio: RadioMetadata = field(default_factory=RadioMetadata)


@dataclass(frozen=True)
class NativeDiagnostics:
    status_code: int
    status_name: str
    event_code: int
    txrx_flags: int


@dataclass(frozen=True)
class SendResult:
    ok: bool
    ack: bool
    downlink: Downlink | None = None
    radio: RadioMetadata = field(default_factory=RadioMetadata)
    diagnostics: NativeDiagnostics | None = None


@dataclass(frozen=True)
class JoinResult:
    joined: bool
    duration_ms: int | None = None


@dataclass(frozen=True)
class DeviceStatus:
    configured: bool
    activation: ActivationMode | None
    joined: bool
    last_error: str | None = None
