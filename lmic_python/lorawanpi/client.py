from __future__ import annotations

from pathlib import Path

from .config import ABPConfig, OTAAConfig, RadioConfig, ActivationMode
from .exceptions import LoRaWANConfigurationError
from .native import NativeLMIC, NativeSendResult
from .results import (
    DeviceStatus,
    Downlink,
    JoinResult,
    NativeDiagnostics,
    RadioMetadata,
    SendResult,
)
from .validation import timeout_to_ms, validate_hex, validate_payload, validate_port


class LoRaWAN:
    def __init__(
        self,
        *,
        radio: RadioConfig | None = None,
    ) -> None:
        self._radio = radio or RadioConfig()
        self._native = NativeLMIC()
        self._config: OTAAConfig | ABPConfig | None = None
        self._activation: ActivationMode | None = None
        self._joined = False
        self._last_error: str | None = None

    def configure_otaa(self, *, deveui: str, appeui: str, appkey: str) -> None:
        validate_hex(deveui, 8, "deveui")
        validate_hex(appeui, 8, "appeui")
        validate_hex(appkey, 16, "appkey")
        self._config = OTAAConfig(deveui=deveui, appeui=appeui, appkey=appkey)
        self._activation = "otaa"
        self._joined = False
        self._last_error = None

    def configure_abp(self, *, devaddr: str, nwkskey: str, appskey: str) -> None:
        validate_hex(devaddr, 4, "devaddr")
        validate_hex(nwkskey, 16, "nwkskey")
        validate_hex(appskey, 16, "appskey")
        self._config = ABPConfig(devaddr=devaddr, nwkskey=nwkskey, appskey=appskey)
        self._activation = "abp"
        self._joined = True
        self._last_error = None

    def join(self, *, timeout: float | None = None) -> JoinResult:
        self._require_configured()
        if self._activation == "abp":
            self._joined = True
            self._last_error = None
            return JoinResult(joined=True)

        timeout_ms = timeout_to_ms(timeout, default_ms=60000)
        try:
            self._native.join_otaa(
                self._config,
                timeout_ms=timeout_ms,
                use_leds=self._radio.use_leds,
            )
        except Exception as exc:
            self._last_error = str(exc)
            raise

        self._joined = True
        self._last_error = None
        return JoinResult(joined=True)

    def send(
        self,
        payload: bytes,
        *,
        port: int = 1,
        confirmed: bool = False,
        timeout: float | None = None,
        diagnostics: bool = False,
    ) -> SendResult:
        validate_payload(payload)
        validate_port(port)
        self._require_configured()

        timeout_ms = timeout_to_ms(
            timeout,
            default_ms=60000 if self._activation == "otaa" else 30000,
        )

        try:
            if isinstance(self._config, ABPConfig):
                native_result = self._native.send_abp(
                    self._config,
                    payload,
                    port=port,
                    confirmed=confirmed,
                    use_leds=self._radio.use_leds,
                    timeout_ms=timeout_ms,
                )
            elif isinstance(self._config, OTAAConfig):
                if not self._joined:
                    self.join(timeout=timeout)
                native_result = self._native.send_otaa_after_join(
                    self._config,
                    payload,
                    port=port,
                    confirmed=confirmed,
                    use_leds=self._radio.use_leds,
                    timeout_ms=timeout_ms,
                )
            else:
                raise LoRaWANConfigurationError("device is not configured")
        except Exception as exc:
            self._last_error = str(exc)
            raise

        self._last_error = None
        return self._result_from_native(native_result, diagnostics=diagnostics)

    def status(self) -> DeviceStatus:
        return DeviceStatus(
            configured=self._config is not None,
            activation=self._activation,
            joined=self._joined,
            last_error=self._last_error,
        )

    def _require_configured(self) -> None:
        if self._config is None:
            raise LoRaWANConfigurationError("device is not configured")

    @staticmethod
    def _result_from_native(
        native_result: NativeSendResult,
        *,
        diagnostics: bool,
    ) -> SendResult:
        radio = RadioMetadata(
            rssi_dbm=native_result.rssi_dbm,
            snr_db=native_result.snr_db,
        )
        downlink = None
        if native_result.downlink:
            downlink = Downlink(
                payload=native_result.downlink,
                port=native_result.downlink_port,
                radio=radio,
            )

        native_diagnostics = None
        if diagnostics:
            native_diagnostics = NativeDiagnostics(
                status_code=native_result.status,
                status_name=native_result.status_name,
                event_code=native_result.event,
                txrx_flags=native_result.txrx_flags,
            )

        return SendResult(
            ok=native_result.status == 0,
            ack=native_result.ack,
            downlink=downlink,
            radio=radio,
            diagnostics=native_diagnostics,
        )
