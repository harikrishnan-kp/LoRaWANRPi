from __future__ import annotations

import ctypes
from dataclasses import dataclass
from pathlib import Path

from .config import ABPConfig, OTAAConfig
from .exceptions import LoRaWANNativeError, LoRaWANTimeoutError
from .validation import validate_hex, validate_payload, validate_port


STATUS_NAMES = {
    0: "ok",
    -1: "invalid_result_pointer",
    -2: "invalid_credentials",
    -3: "invalid_payload",
    -4: "join_or_send_timeout",
    -5: "send_timeout_after_join",
    -6: "not_joined",
}


class _NativeResult(ctypes.Structure):
    _fields_ = [
        ("status", ctypes.c_int),
        ("event", ctypes.c_int),
        ("txrx_flags", ctypes.c_int),
        ("ack", ctypes.c_int),
        ("nack", ctypes.c_int),
        ("rssi_dbm", ctypes.c_int),
        ("snr_db", ctypes.c_float),
        ("downlink_port", ctypes.c_int),
        ("downlink_len", ctypes.c_uint8),
        ("downlink", ctypes.c_uint8 * 64),
    ]


@dataclass(frozen=True)
class NativeSendResult:
    status: int
    status_name: str
    event: int
    txrx_flags: int
    ack: bool
    nack: bool
    rssi_dbm: int
    snr_db: float
    downlink_port: int | None
    downlink: bytes


def default_library_path() -> Path:
    return Path(__file__).resolve().with_name("liblorawanpi.so")


class NativeLMIC:
    def __init__(self) -> None:
        path = default_library_path()
        if not path.exists():
            raise LoRaWANNativeError(
                f"native library not found at {path}; run `make` in lmic_python first",
                status_code=-1,
                status_name="native_library_not_found",
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
            ctypes.c_int,
            ctypes.POINTER(_NativeResult),
        ]
        self._send_otaa.restype = ctypes.c_int

        self._send_otaa_after_join = self._lib.lmic_rpi_send_otaa_after_join
        self._send_otaa_after_join.argtypes = [
            ctypes.POINTER(ctypes.c_uint8),
            ctypes.c_uint8,
            ctypes.c_uint8,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.POINTER(_NativeResult),
        ]
        self._send_otaa_after_join.restype = ctypes.c_int

        self._join_otaa = self._lib.lmic_rpi_join_otaa
        self._join_otaa.argtypes = [
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.POINTER(_NativeResult),
        ]
        self._join_otaa.restype = ctypes.c_int

    def send_abp(
        self,
        config: ABPConfig,
        payload: bytes,
        *,
        port: int,
        confirmed: bool,
        use_leds: bool,
        timeout_ms: int,
    ) -> NativeSendResult:
        validate_hex(config.devaddr, 4, "devaddr")
        validate_hex(config.nwkskey, 16, "nwkskey")
        validate_hex(config.appskey, 16, "appskey")
        return self._call_send(
            self._send_abp,
            config.devaddr,
            config.nwkskey,
            config.appskey,
            payload,
            port=port,
            confirmed=confirmed,
            use_leds=use_leds,
            timeout_ms=timeout_ms,
            operation="send",
        )

    def send_otaa(
        self,
        config: OTAAConfig,
        payload: bytes,
        *,
        port: int,
        confirmed: bool,
        use_leds: bool,
        timeout_ms: int,
    ) -> NativeSendResult:
        validate_hex(config.deveui, 8, "deveui")
        validate_hex(config.appeui, 8, "appeui")
        validate_hex(config.appkey, 16, "appkey")
        return self._call_send(
            self._send_otaa,
            config.deveui,
            config.appeui,
            config.appkey,
            payload,
            port=port,
            confirmed=confirmed,
            use_leds=use_leds,
            timeout_ms=timeout_ms,
            operation="join/send",
        )

    def send_otaa_after_join(
        self,
        config: OTAAConfig,
        payload: bytes,
        *,
        port: int,
        confirmed: bool,
        use_leds: bool,
        timeout_ms: int,
    ) -> NativeSendResult:
        validate_payload(payload)
        validate_port(port)
        return self._call_send_existing_session(
            self._send_otaa_after_join,
            payload,
            port=port,
            confirmed=confirmed,
            use_leds=use_leds,
            timeout_ms=timeout_ms,
            operation="send after join",
        )

    def join_otaa(
        self,
        config: OTAAConfig,
        *,
        timeout_ms: int,
        use_leds: bool,
    ) -> None:
        validate_hex(config.deveui, 8, "deveui")
        validate_hex(config.appeui, 8, "appeui")
        validate_hex(config.appkey, 16, "appkey")

        native_result = _NativeResult()
        rc = self._join_otaa(
            config.deveui.encode("ascii"),
            config.appeui.encode("ascii"),
            config.appkey.encode("ascii"),
            int(use_leds),
            timeout_ms,
            ctypes.byref(native_result),
        )

        if rc != 0:
            error = self._error_for_status(rc, "join")
            if rc == -4:
                raise LoRaWANTimeoutError(error)
            raise LoRaWANNativeError(
                error,
                status_code=rc,
                status_name=STATUS_NAMES.get(rc, "native_error"),
            )

    def _call_send(
        self,
        function: object,
        first_key: str,
        second_key: str,
        third_key: str,
        payload: bytes,
        *,
        port: int,
        confirmed: bool,
        use_leds: bool,
        timeout_ms: int,
        operation: str,
    ) -> NativeSendResult:
        validate_payload(payload)
        validate_port(port)

        payload_buffer = (ctypes.c_uint8 * max(len(payload), 1))()
        for index, value in enumerate(payload):
            payload_buffer[index] = value

        native_result = _NativeResult()
        rc = function(
            first_key.encode("ascii"),
            second_key.encode("ascii"),
            third_key.encode("ascii"),
            payload_buffer,
            len(payload),
            port,
            int(confirmed),
            int(use_leds),
            timeout_ms,
            ctypes.byref(native_result),
        )

        result = self._to_native_result(native_result)
        if rc != 0:
            error = self._error_for_status(rc, operation)
            if rc in {-4, -5}:
                raise LoRaWANTimeoutError(error)
            raise LoRaWANNativeError(
                error,
                status_code=rc,
                status_name=STATUS_NAMES.get(rc, "native_error"),
            )
        return result

    def _call_send_existing_session(
        self,
        function: object,
        payload: bytes,
        *,
        port: int,
        confirmed: bool,
        use_leds: bool,
        timeout_ms: int,
        operation: str,
    ) -> NativeSendResult:
        validate_payload(payload)
        validate_port(port)

        payload_buffer = (ctypes.c_uint8 * max(len(payload), 1))()
        for index, value in enumerate(payload):
            payload_buffer[index] = value

        native_result = _NativeResult()
        rc = function(
            payload_buffer,
            len(payload),
            port,
            int(confirmed),
            int(use_leds),
            timeout_ms,
            ctypes.byref(native_result),
        )

        result = self._to_native_result(native_result)
        if rc != 0:
            error = self._error_for_status(rc, operation)
            if rc in {-4, -5}:
                raise LoRaWANTimeoutError(error)
            raise LoRaWANNativeError(
                error,
                status_code=rc,
                status_name=STATUS_NAMES.get(rc, "native_error"),
            )
        return result

    @staticmethod
    def _to_native_result(native_result: _NativeResult) -> NativeSendResult:
        downlink_port = native_result.downlink_port
        return NativeSendResult(
            status=native_result.status,
            status_name=STATUS_NAMES.get(native_result.status, "native_error"),
            event=native_result.event,
            txrx_flags=native_result.txrx_flags,
            ack=bool(native_result.ack),
            nack=bool(native_result.nack),
            rssi_dbm=native_result.rssi_dbm,
            snr_db=float(native_result.snr_db),
            downlink_port=downlink_port if downlink_port > 0 else None,
            downlink=bytes(native_result.downlink[: native_result.downlink_len]),
        )

    @staticmethod
    def _error_for_status(status: int, operation: str) -> str:
        status_name = STATUS_NAMES.get(status, "native_error")
        return f"LoRaWAN {operation} failed: {status_name} ({status})"
