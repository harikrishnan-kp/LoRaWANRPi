from __future__ import annotations


MAX_PAYLOAD_BYTES = 51
MIN_APP_PORT = 1
MAX_APP_PORT = 223


def validate_hex(value: str, expected_bytes: int, name: str) -> str:
    if len(value) != expected_bytes * 2:
        raise ValueError(f"{name} must be {expected_bytes * 2} hex characters")
    try:
        bytes.fromhex(value)
    except ValueError as exc:
        raise ValueError(f"{name} must contain only hex characters") from exc
    return value


def validate_payload(payload: bytes) -> bytes:
    if not isinstance(payload, bytes):
        raise TypeError("payload must be bytes")
    if len(payload) > MAX_PAYLOAD_BYTES:
        raise ValueError(f"payload must be {MAX_PAYLOAD_BYTES} bytes or fewer")
    return payload


def validate_port(port: int) -> int:
    if not MIN_APP_PORT <= port <= MAX_APP_PORT:
        raise ValueError(f"port must be between {MIN_APP_PORT} and {MAX_APP_PORT}")
    return port


def timeout_to_ms(timeout: float | None, default_ms: int) -> int:
    if timeout is None:
        return default_ms
    if timeout < 0:
        raise ValueError("timeout must be non-negative")
    return int(timeout * 1000)
