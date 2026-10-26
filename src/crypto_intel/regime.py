"""Regime classification for market series."""

from __future__ import annotations

from statistics import fmean

from crypto_intel.models import Candle, Regime


def classify(candles: list[Candle]) -> Regime:
    if len(candles) < 8:
        return Regime.RANGE
    closes = [c.close for c in candles[-8:]]
    move = abs(closes[-1] / closes[0] - 1.0)
    ranges = [(c.high - c.low) / c.close for c in candles[-8:] if c.close]
    avg_range = fmean(ranges) if ranges else 0.0
    if avg_range >= 0.035:
        return Regime.STRESS
    if move >= 0.025 and avg_range < 0.035:
        return Regime.TREND
    return Regime.RANGE


def atr_pct(candles: list[Candle]) -> float:
    ranges = [(c.high - c.low) / c.close for c in candles[-14:] if c.close]
    return fmean(ranges) if ranges else 0.0
