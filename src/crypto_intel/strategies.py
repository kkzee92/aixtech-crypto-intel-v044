"""Asset-class strategy research rules.

Transparent heuristics for paper research. Not forecasts and not a recommendation
to trade. Each class has an entry, an invalidation, and a regime overlay.
Version 0.44 adds Ichimoku-style cloud proxy and ADX trend-strength confirmation.
"""

from __future__ import annotations

from statistics import fmean, pstdev

from crypto_intel.models import AssetClass, Candle, Side, Signal
from crypto_intel.regime import Regime, atr_pct, classify

PLAYBOOK: dict[AssetClass, dict[str, str]] = {
    AssetClass.MAJOR: {
        "hypothesis": "Liquid majors trend with multi-factor, Ichimoku cloud, and ADX strength confirmation, except under stress.",
        "entry": "Fast EMA above slow, RSI 45-70, volume ok, Ichimoku price above cloud, ADX >25, multi-TF aligned, adaptive scale.",
        "invalidation": "Stress, RSI >70, thin volume, weak ADX, price inside or below cloud, multi-TF mismatch.",
        "horizon": "8 bars mean-reversion, 20 bars trend",
    },
    AssetClass.LARGE_CAP_ALT: {
        "hypothesis": "Breakouts without volume or strength are noise.",
        "entry": "Close above prior high, volume 1.2x, ADX >20, Ichimoku above cloud, non-stress.",
        "invalidation": "Stress, low volume, weak ADX, or below cloud.",
        "horizon": "12 bars",
    },
    AssetClass.STABLECOIN: {
        "hypothesis": "The useful signal is a peg break.",
        "entry": "Deviation of 50 bps or more raises an alert. No order.",
        "invalidation": "Not applicable. Size stays zero.",
        "horizon": "1 bar monitor",
    },
    AssetClass.DEFI: {
        "hypothesis": "Trend only in calm regime with strength confirmation.",
        "entry": "Close above EMA, vol low, ADX >22, Ichimoku above, non-stress.",
        "invalidation": "Stress, high vol, weak ADX, or below cloud.",
        "horizon": "10 bars",
    },
    AssetClass.MEME: {
        "hypothesis": "Most bursts are untradeable. Qualified with strength.",
        "entry": "15% burst, rising volume, ADX rising, not extended.",
        "invalidation": "Thin liquidity or chase extension.",
        "horizon": "3 bars",
    },
    AssetClass.L2: {
        "hypothesis": "L2 relative strength versus benchmark, with strength filter.",
        "entry": "Excess return >3%, benchmark non-stress, ADX >18.",
        "invalidation": "Missing benchmark, benchmark stress, or weak ADX.",
        "horizon": "12 bars",
    },
    AssetClass.RWA: {
        "hypothesis": "Tokenised assets should be slow with strength confirmation.",
        "entry": "Slow trend, gap <8%, ADX >15, non-stress.",
        "invalidation": "Gap >8% or stress.",
        "horizon": "24 bars",
    },
    AssetClass.PERPETUAL: {
        "hypothesis": "Negative funding with contained drift and strength.",
        "entry": "Funding <= -5 bps, |drift| <4%, ADX contained.",
        "invalidation": "Crowded funding or excess drift.",
        "horizon": "8 bars",
    },
}


def _returns(closes: list[float]) -> list[float]:
    return [closes[i] / closes[i - 1] - 1.0 for i in range(1, len(closes))]


def _ema(values: list[float], span: int) -> float:
    alpha = 2.0 / (span + 1)
    value = values[0]
    for point in values[1:]:
        value = alpha * point + (1 - alpha) * value
    return value


def _rsi(closes: list[float], period: int = 14) -> float:
    changes = _returns(closes[-(period + 1) :])
    gains = [max(change, 0.0) for change in changes]
    losses = [abs(min(change, 0.0)) for change in changes]
    average_loss = fmean(losses) if losses else 0.0
    if average_loss == 0:
        return 100.0
    rs = fmean(gains) / average_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _adx_proxy(candles: list[Candle], period: int = 14) -> float:
    """Simple ADX-style trend strength proxy from directional movement."""
    if len(candles) < period + 1:
        return 0.0
    plus_dm = []
    minus_dm = []
    tr = []
    for i in range(1, len(candles)):
        up = candles[i].high - candles[i - 1].high
        down = candles[i - 1].low - candles[i].low
        plus_dm.append(max(up, 0.0) if up > down else 0.0)
        minus_dm.append(max(down, 0.0) if down > up else 0.0)
        tr.append(max(candles[i].high - candles[i].low, abs(candles[i].high - candles[i - 1].close), abs(candles[i].low - candles[i - 1].close)))
    if not tr:
        return 0.0
    avg_plus = fmean(plus_dm[-period:]) / (fmean(tr[-period:]) or 1)
    avg_minus = fmean(minus_dm[-period:]) / (fmean(tr[-period:]) or 1)
    dx = abs(avg_plus - avg_minus) / (avg_plus + avg_minus or 1) * 100
    return min(dx, 100.0)


def _ichimoku_proxy(candles: list[Candle]) -> tuple[float, float, float]:
    """Ichimoku-style: Tenkan (9), Kijun (26), Senkou A proxy."""
    if len(candles) < 26:
        return 0.0, 0.0, 0.0
    highs9 = [c.high for c in candles[-9:]]
    lows9 = [c.low for c in candles[-9:]]
    tenkan = (max(highs9) + min(lows9)) / 2
    highs26 = [c.high for c in candles[-26:]]
    lows26 = [c.low for c in candles[-26:]]
    kijun = (max(highs26) + min(lows26)) / 2
    senkou_a = (tenkan + kijun) / 2
    return tenkan, kijun, senkou_a


def _atr_pct(candles: list[Candle]) -> float:
    ranges = [(c.high - c.low) / c.close for c in candles[-14:] if c.close]
    return fmean(ranges) if ranges else 0.0


def _base(candles: list[Candle], side: Side, confidence: float, reason: str, size: float, bars: int) -> Signal:
    last = candles[-1]
    regime = classify(candles)
    return Signal(
        symbol=last.symbol,
        asset_class=last.asset_class,
        side=side,
        confidence=round(max(0.0, min(confidence, 1.0)), 4),
        reason=f"{reason}; regime={regime.value}",
        stop_distance_pct=round(max(_atr_pct(candles) * 1.5, 0.01), 4),
        size_fraction=size,
        horizon_bars=bars,
    )


def signal_for(candles: list[Candle], benchmark: list[Candle] | None = None) -> Signal:
    if len(candles) < 8:
        raise ValueError("need at least 8 candles")
    asset_class = candles[-1].asset_class
    closes = [c.close for c in candles]
    regime = classify(candles)
    if asset_class is AssetClass.MAJOR:
        return _major(candles, closes, regime)
    if asset_class is AssetClass.LARGE_CAP_ALT:
        return _breakout(candles, closes, size=0.04, bars=12, regime=regime)
    if asset_class is AssetClass.STABLECOIN:
        return _stable(candles)
    if asset_class is AssetClass.DEFI:
        return _defi(candles, closes, regime)
    if asset_class is AssetClass.MEME:
        return _meme(candles, closes)
    if asset_class is AssetClass.L2:
        return _l2(candles, closes, benchmark)
    if asset_class is AssetClass.RWA:
        return _rwa(candles, closes, regime)
    return _perpetual(candles, closes)


def _major(candles: list[Candle], closes: list[float], regime: Regime) -> Signal:
    fast, slow = _ema(closes, 5), _ema(closes, 13)
    rsi = _rsi(closes)
    adx = _adx_proxy(candles)
    tenkan, kijun, senkou = _ichimoku_proxy(candles)
    price = closes[-1]
    if regime is Regime.STRESS:
        return _base(candles, Side.FLAT, 0.45, "major stress: stand aside", 0.0, 1)
    if fast > slow and 45 <= rsi <= 70 and adx > 25 and price > senkou:
        return _base(candles, Side.LONG, 0.78, "major trend: EMA + ADX>25 + Ichimoku above cloud", 0.06, 20)
    if regime is Regime.RANGE and rsi < 30 and price > senkou * 0.98:
        return _base(candles, Side.LONG, 0.64, "major mean-reversion: washed RSI, near cloud", 0.03, 8)
    return _base(candles, Side.FLAT, 0.4, "major: no confirmed edge", 0.0, 1)


def _breakout(candles: list[Candle], closes: list[float], size: float, bars: int, regime: Regime) -> Signal:
    if regime is Regime.STRESS:
        return _base(candles, Side.FLAT, 0.4, "breakout suppressed in stress", 0.0, 1)
    window = closes[-6:-1]
    volume_now = candles[-1].volume
    volume_base = fmean(c.volume for c in candles[-6:-1])
    adx = _adx_proxy(candles)
    _, _, senkou = _ichimoku_proxy(candles)
    if closes[-1] > max(window) and volume_now > volume_base * 1.2 and adx > 20 and closes[-1] > senkou:
        return _base(candles, Side.LONG, 0.73, "breakout with volume, ADX, and Ichimoku", size, bars)
    return _base(candles, Side.FLAT, 0.35, "no confirmed breakout", 0.0, 1)


def _stable(candles: list[Candle]) -> Signal:
    deviation = abs(candles[-1].close - 1.0)
    if deviation >= 0.005:
        return _base(candles, Side.ALERT, 0.92, f"stablecoin depeg monitor: deviation {deviation:.4f}", 0.0, 1)
    if deviation >= 0.002:
        return _base(candles, Side.ALERT, 0.7, f"stablecoin watch band: deviation {deviation:.4f}", 0.0, 1)
    return _base(candles, Side.FLAT, 0.8, "stablecoin inside peg band", 0.0, 1)


def _defi(candles: list[Candle], closes: list[float], regime: Regime) -> Signal:
    realised = fmean(abs(v) for v in _returns(closes[-8:]))
    adx = _adx_proxy(candles)
    _, _, senkou = _ichimoku_proxy(candles)
    if regime is Regime.STRESS or realised > 0.06:
        return _base(candles, Side.FLAT, 0.48, "defi volatility regime: stand aside", 0.0, 1)
    if closes[-1] > _ema(closes, 8) and adx > 22 and closes[-1] > senkou:
        return _base(candles, Side.LONG, 0.71, "defi trend in calm regime with ADX and Ichimoku", 0.02, 10)
    return _base(candles, Side.FLAT, 0.4, "defi: no calm trend", 0.0, 1)


def _meme(candles: list[Candle], closes: list[float]) -> Signal:
    liquidity = fmean(c.volume for c in candles[-5:])
    burst = closes[-1] / closes[-4] - 1.0
    extension = closes[-1] / closes[-8] - 1.0
    adx = _adx_proxy(candles)
    if liquidity < 1000:
        return _base(candles, Side.FLAT, 0.2, "meme liquidity proxy too thin", 0.0, 1)
    if extension > 0.40:
        return _base(candles, Side.FLAT, 0.35, "meme chase filter: 8-bar extension too large", 0.0, 1)
    if burst > 0.15 and candles[-1].volume > candles[-2].volume and adx > 15:
        return _base(candles, Side.LONG, 0.79, "meme momentum burst with ADX; hard time stop", 0.005, 3)
    return _base(candles, Side.FLAT, 0.3, "meme: no qualified burst", 0.0, 1)


def _l2(candles: list[Candle], closes: list[float], benchmark: list[Candle] | None) -> Signal:
    if not benchmark or len(benchmark) < 8:
        return _base(candles, Side.FLAT, 0.3, "l2 requires a benchmark series", 0.0, 1)
    if classify(benchmark) is Regime.STRESS:
        return _base(candles, Side.FLAT, 0.42, "l2 benchmark in stress", 0.0, 1)
    own = closes[-1] / closes[-6] - 1.0
    bench_closes = [c.close for c in benchmark]
    bench = bench_closes[-1] / bench_closes[-6] - 1.0
    adx = _adx_proxy(candles)
    if own - bench > 0.03 and adx > 18:
        return _base(candles, Side.LONG, 0.72, "l2 relative strength with ADX", 0.03, 12)
    return _base(candles, Side.FLAT, 0.4, "l2 not leading benchmark", 0.0, 1)


def _rwa(candles: list[Candle], closes: list[float], regime: Regime) -> Signal:
    gap = candles[-1].open / candles[-2].close - 1.0
    adx = _adx_proxy(candles)
    if abs(gap) > 0.08 or regime is Regime.STRESS:
        return _base(candles, Side.FLAT, 0.5, "rwa gap or stress halt", 0.0, 1)
    if closes[-1] > _ema(closes, 8) and closes[-1] > closes[-5] and adx > 15:
        return _base(candles, Side.LONG, 0.68, "rwa slow trend with ADX", 0.02, 24)
    return _base(candles, Side.FLAT, 0.4, "rwa: no slow trend", 0.0, 1)


def _perpetual(candles: list[Candle], closes: list[float]) -> Signal:
    funding = candles[-1].funding_rate
    drift = closes[-1] / closes[-6] - 1.0
    adx = _adx_proxy(candles)
    if funding >= 0.001:
        return _base(candles, Side.ALERT, 0.7, "perp funding crowded: monitor, no carry", 0.0, 1)
    if funding <= -0.0005 and abs(drift) < 0.04 and adx < 40:
        return _base(candles, Side.LONG, 0.76, "perp funding carry: negative funding, basis contained, ADX ok", 0.02, 8)
    if funding <= -0.0005:
        return _base(candles, Side.FLAT, 0.5, "perp funding attractive but drift not contained", 0.0, 1)
    return _base(candles, Side.FLAT, 0.4, "perp: no carry edge", 0.0, 1)
