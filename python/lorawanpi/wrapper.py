from __future__ import annotations

import ctypes
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


class LoraWanPiError(RuntimeError):
    pass


class _NativeResult(ctypes.Structure):
    _fields_ = [
        ("status", ctypes.c_int),
        ("event", ctypes.c_int),
        ("txrx_flags", ctypes.c_int),
        ("ack", ctypes.c_int),
        ("nack", ctypes.c_int),
        ("rssi_dbm", ctypes.c_int),
        ("snr_db", ctypes.c_float),
        ("downlink_len", ctypes.c_uint8),
        ("downlink", ctypes.c_uint8 * 64),
    ]


@dataclass(frozen=True)
class SendResult:
    status: int
    event: int
    txrx_flags: int
    ack: bool
    nack: bool
    rssi_dbm: int
    snr_db: float
    downlink: bytes


def _default_library_path() -> Path:
    return Path(__file__).resolve().with_name("liblorawanpi.so")


def _validate_hex(value: str, expected_bytes: int, name: str) -> str:
    if len(value) != expected_bytes * 2:
        raise ValueError(f"{name} must be {expected_bytes * 2} hex characters")
    try:
        bytes.fromhex(value)
    except ValueError as exc:
        raise ValueError(f"{name} must contain only hex characters") from exc
    return value


def encode_rain_payload(rain_mm: float) -> bytes:
    fixed = int(rain_mm * 100)
    if fixed < 0 or fixed > 0xFFFF:
        raise ValueError("rain_mm must fit in an unsigned 16-bit fixed-point payload")
    return fixed.to_bytes(2, "big")


class LoraWanPi:
    def __init__(self, library_path: Optional[str | Path] = None) -> None:
        path = Path(library_path) if library_path is not None else _default_library_path()
        if not path.exists():
            raise LoraWanPiError(
                f"native library not found at {path}; run `make` in python first"
            )

        self._lib = ctypes.CDLL(str(path))
        self._send_abp = self._lib.lmic_rpi_send_abp
        self._send_abp.argtypes = [
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_uint8),
            ctypes.c_uint8,
            ctypes.c_uint8,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.POINTER(_NativeResult),
        ]
        self._send_abp.restype = ctypes.c_int

        self._send_otaa = self._lib.lmic_rpi_send_otaa
        self._send_otaa.argtypes = [
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_uint8),
            ctypes.c_uint8,
            ctypes.c_uint8,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.POINTER(_NativeResult),
        ]
        self._send_otaa.restype = ctypes.c_int

    def send_abp(
        self,
        devaddr: str,
        nwkskey: str,
        appskey: str,
        payload: bytes,
        *,
        port: int = 1,
        use_leds: bool = True,
        timeout_ms: int = 30000,
    ) -> SendResult:
        _validate_hex(devaddr, 4, "devaddr")
        _validate_hex(nwkskey, 16, "nwkskey")
        _validate_hex(appskey, 16, "appskey")

        if not 1 <= port <= 223:
            raise ValueError("port must be between 1 and 223")
        if len(payload) > 51:
            raise ValueError("payload must be 51 bytes or fewer")
        if timeout_ms < 0:
            raise ValueError("timeout_ms must be non-negative")

        payload_buffer = (ctypes.c_uint8 * max(len(payload), 1))()
        for index, value in enumerate(payload):
            payload_buffer[index] = value

        native_result = _NativeResult()
        rc = self._send_abp(
            devaddr.encode("ascii"),
            nwkskey.encode("ascii"),
            appskey.encode("ascii"),
            payload_buffer,
            len(payload),
            port,
            int(use_leds),
            timeout_ms,
            ctypes.byref(native_result),
        )

        result = SendResult(
            status=native_result.status,
            event=native_result.event,
            txrx_flags=native_result.txrx_flags,
            ack=bool(native_result.ack),
            nack=bool(native_result.nack),
            rssi_dbm=native_result.rssi_dbm,
            snr_db=float(native_result.snr_db),
            downlink=bytes(native_result.downlink[: native_result.downlink_len]),
        )

        if rc != 0:
            raise LoraWanPiError(f"send_abp failed with native status {rc}")

        return result

    def send_otaa(
        self,
        deveui: str,
        appeui: str,
        appkey: str,
        payload: bytes,
        *,
        port: int = 1,
        use_leds: bool = True,
        timeout_ms: int = 60000,
    ) -> SendResult:
        _validate_hex(deveui, 8, "deveui")
        _validate_hex(appeui, 8, "appeui")
        _validate_hex(appkey, 16, "appkey")

        if not 1 <= port <= 223:
            raise ValueError("port must be between 1 and 223")
        if len(payload) > 51:
            raise ValueError("payload must be 51 bytes or fewer")
        if timeout_ms < 0:
            raise ValueError("timeout_ms must be non-negative")

        payload_buffer = (ctypes.c_uint8 * max(len(payload), 1))()
        for index, value in enumerate(payload):
            payload_buffer[index] = value

        native_result = _NativeResult()
        rc = self._send_otaa(
            deveui.encode("ascii"),
            appeui.encode("ascii"),
            appkey.encode("ascii"),
            payload_buffer,
            len(payload),
            port,
            int(use_leds),
            timeout_ms,
            ctypes.byref(native_result),
        )

        result = SendResult(
            status=native_result.status,
            event=native_result.event,
            txrx_flags=native_result.txrx_flags,
            ack=bool(native_result.ack),
            nack=bool(native_result.nack),
            rssi_dbm=native_result.rssi_dbm,
            snr_db=float(native_result.snr_db),
            downlink=bytes(native_result.downlink[: native_result.downlink_len]),
        )

        if rc != 0:
            raise LoraWanPiError(f"send_otaa failed with native status {rc}")

        return result


def send_abp(
    devaddr: str,
    nwkskey: str,
    appskey: str,
    payload: bytes,
    *,
    port: int = 1,
    use_leds: bool = True,
    timeout_ms: int = 30000,
    library_path: Optional[str | Path] = None,
) -> SendResult:
    return LoraWanPi(library_path).send_abp(
        devaddr,
        nwkskey,
        appskey,
        payload,
        port=port,
        use_leds=use_leds,
        timeout_ms=timeout_ms,
    )


def send_otaa(
    deveui: str,
    appeui: str,
    appkey: str,
    payload: bytes,
    *,
    port: int = 1,
    use_leds: bool = True,
    timeout_ms: int = 60000,
    library_path: Optional[str | Path] = None,
) -> SendResult:
    return LoraWanPi(library_path).send_otaa(
        deveui,
        appeui,
        appkey,
        payload,
        port=port,
        use_leds=use_leds,
        timeout_ms=timeout_ms,
    )


def send_rain_abp(
    devaddr: str,
    nwkskey: str,
    appskey: str,
    rain_mm: float,
    *,
    use_leds: bool = True,
    timeout_ms: int = 30000,
    library_path: Optional[str | Path] = None,
) -> SendResult:
    return LoraWanPi(library_path).send_abp(
        devaddr,
        nwkskey,
        appskey,
        encode_rain_payload(rain_mm),
        port=1,
        use_leds=use_leds,
        timeout_ms=timeout_ms,
    )


def send_rain_otaa(
    deveui: str,
    appeui: str,
    appkey: str,
    rain_mm: float,
    *,
    use_leds: bool = True,
    timeout_ms: int = 60000,
    library_path: Optional[str | Path] = None,
) -> SendResult:
    return LoraWanPi(library_path).send_otaa(
        deveui,
        appeui,
        appkey,
        encode_rain_payload(rain_mm),
        port=1,
        use_leds=use_leds,
        timeout_ms=timeout_ms,
    )
