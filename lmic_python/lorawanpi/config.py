from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


ActivationMode = Literal["otaa", "abp"]


@dataclass(frozen=True)
class OTAAConfig:
    deveui: str
    appeui: str
    appkey: str


@dataclass(frozen=True)
class ABPConfig:
    devaddr: str
    nwkskey: str
    appskey: str


@dataclass(frozen=True)
class RadioConfig:
    region: str = "EU868"
    data_rate: int | None = None
    tx_power: int | None = None
    adr: bool = False
    link_check: bool = False
    use_leds: bool = True
