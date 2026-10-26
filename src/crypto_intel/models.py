"""Core models for the paper-only crypto intel system."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AssetClass(Enum):
    MAJOR = "major"
    LARGE_CAP_ALT = "large_cap_alt"
    STABLECOIN = "stablecoin"
    DEFI = "defi"
    MEME = "meme"
    L2 = "l2"
    RWA = "rwa"
    PERPETUAL = "perpetual"


class Side(Enum):
    LONG = "long"
    SHORT = "short"
    FLAT = "flat"
    ALERT = "alert"


class ExecutionMode(Enum):
    PAPER = "paper"
    HALTED = "halted"
    # LIVE is refused


class Regime(Enum):
    TREND = "trend"
    RANGE = "range"
    STRESS = "stress"


@dataclass
class Candle:
    symbol: str
    asset_class: AssetClass
    open: float
    high: float
    low: float
    close: float
    volume: float
    funding_rate: float = 0.0
    timestamp: str = ""


@dataclass
class Signal:
    symbol: str
    asset_class: AssetClass
    side: Side
    confidence: float
    reason: str
    stop_distance_pct: float
    size_fraction: float
    horizon_bars: int


@dataclass
class AuditEvent:
    sequence: int
    action: str
    detail: str
    previous_hash: str
    digest: str
    sealed_digest: str = ""
    timestamp: str = ""
