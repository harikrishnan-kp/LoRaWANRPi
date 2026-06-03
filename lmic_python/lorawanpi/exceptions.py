from __future__ import annotations


class LoRaWANError(RuntimeError):
    """Base error for LoRaWAN application-level failures."""


class LoRaWANConfigurationError(LoRaWANError):
    """Raised when an operation requires missing or invalid configuration."""


class LoRaWANTimeoutError(LoRaWANError):
    """Raised when join or transmit does not complete before the timeout."""


class LoRaWANNativeError(LoRaWANError):
    """Raised when the native LMIC layer returns an unsuccessful status."""

    def __init__(self, message: str, *, status_code: int, status_name: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.status_name = status_name
