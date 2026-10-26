# v0.44 enhancements: Ichimoku-style proxy, ADX strength, and strengthened zero-trust controls

Research only. Paper-only. Not financial, legal, or security advice.

## Strategy upgrades (per asset class)

- **Ichimoku-style cloud proxy**: Tenkan/Kijun/Senkou A added to major, large-cap, DeFi, and shared overlays. Long signals prefer price above the cloud.
- **ADX trend-strength proxy**: Directional movement based strength filter. Thresholds per class (e.g. >25 for majors).
- **Multi-factor refined**: Combines EMA, RSI, volume, Ichimoku, and ADX for higher-quality paper signals.
- **All classes**: Reasons include ADX and cloud position for transparency.
- Adaptive vol scaling retained where applicable.

All rules remain transparent heuristics on synthetic candles. No edge or future-return claim is made.

## Cyber / data security upgrades

- Expanded SECRET_PATTERNS for BIP39 seed phrases, private keys (0x64), and additional token formats.
- AuditLog supports sealed multi-hash lineage via secondary SHA-256 wrap.
- New classifications for seed phrases and private keys.
- Zero-trust input gate strengthened; redaction before any chain append.
- Timestamps on every audit event.

## Threat model additions

| Threat | Control |
|---|---|
| Seed phrase or private key paste | Expanded patterns + redaction |
| Weak trend oversized risk | ADX filter in signal generation |
| Audit tamper | Sealed multi-hash + timestamped chain |
| Cloud injection via fixture | Source attestation + SYNTHETIC label required |

## Operating notes

- Still no order router, no trade/withdrawal keys, no live mode. `assert_paper_only` unchanged.
- Human review required before any kill-switch clear.
- Promote any signal only via a separate, human-approved system.

See also prior version notes in the base repository.
