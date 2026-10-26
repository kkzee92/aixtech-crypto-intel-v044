# Asset-class strategy notes (v0.44)

These rules are research heuristics. Each class has an edge hypothesis, an entry, an invalidation, a horizon, and a size cap. They are not a promise of return. Version 0.44 adds Ichimoku cloud proxy and ADX strength filters.

Regime labels, from `regime.py`:

- **trend**: eight-bar move of at least 2.5% and bar range under the stress band
- **range**: neither stress nor trend
- **stress**: average bar range at least 3.5% of price; directional ideas stand aside

## Major

Hypothesis: liquid majors trend with multi-factor confirmation including ADX and price above Ichimoku cloud. Mean reversion only in range. Cap 8%. Horizon 8 or 20 bars. Research cost 8 bps.

## Large-cap alt

Hypothesis: breakouts require volume, ADX, and cloud confirmation. Cap 4%. Cost 14 bps.

## Stablecoin

Hypothesis: the useful signal is a peg break. 20 bp watch, 50 bp depeg. Size zero.

## DeFi

Hypothesis: trend only in calm regime with ADX and cloud. Cap 2%. Cost 22 bps.

## Meme

Hypothesis: qualified burst with ADX. Cap 0.5%. Cost 45 bps. Horizon 3 bars.

## L2

Hypothesis: relative strength with ADX versus non-stress benchmark. Cap 3%. Cost 16 bps.

## RWA

Hypothesis: slow trend with ADX; gap or stress halt. Cap 2%. Cost 12 bps.

## Perpetual

Hypothesis: negative funding with contained drift and ADX. Cap 2%. Cost 10 bps.

## Still out of scope

- Live order routing, withdrawal, and trade API keys.
- A broker adapter. That would be a separate human-approved system.
- Claims about future returns. Scores describe the synthetic fixture.
