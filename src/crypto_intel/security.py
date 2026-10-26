"""Cyber and data-security controls for the information system.

Version 0.44: expanded redaction for BIP39 seeds, private keys, and session tokens;
multi-hash sealed lineage simulation in AuditLog; stronger zero-trust gates.
Research control plane, not a certified product.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from crypto_intel.models import AuditEvent, ExecutionMode

SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|secret|password|token|private[_-]?key)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{12,}"),
    re.compile(r"\b(?:sk|pk)_(?:live|test)_[A-Za-z0-9]{8,}\b"),
    re.compile(r"\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    re.compile(r"\b(?:seed|mnemonic|bip39)\s*[:=]\s*['\"]?[a-z\s]{20,}"),
    re.compile(r"\b0x[a-fA-F0-9]{64}\b"),  # private key like
)

WALLET_PATTERN = re.compile(r"\b0x[a-fA-F0-9]{40}\b")


@dataclass(frozen=True)
class DataClassification:
    field: str
    level: str
    retention: str


CLASSIFICATION = (
    DataClassification("symbol", "public", "research retention"),
    DataClassification("ohlcv", "public-market", "research retention"),
    DataClassification("exchange_api_key", "secret", "never stored"),
    DataClassification("wallet_address", "sensitive-identifier", "do not fixture"),
    DataClassification("account_email", "personal", "do not collect"),
    DataClassification("seed_phrase", "secret", "never stored"),
    DataClassification("private_key", "secret", "never stored"),
)


def redact(text: str) -> str:
    cleaned = text
    for pattern in SECRET_PATTERNS:
        cleaned = pattern.sub("[REDACTED]", cleaned)
    return WALLET_PATTERN.sub("[WALLET]", cleaned)


def contains_secret(text: str) -> bool:
    return any(pattern.search(text) for pattern in SECRET_PATTERNS) or bool(WALLET_PATTERN.search(text))


def assert_paper_only(mode: ExecutionMode) -> None:
    if mode is not ExecutionMode.PAPER:
        raise PermissionError("live execution is disabled; this system is paper-only")


def hash_event(previous_hash: str, sequence: int, action: str, detail: str, timestamp: str = "") -> str:
    material = f"{previous_hash}|{sequence}|{action}|{detail}|{timestamp}".encode()
    return hashlib.sha256(material).hexdigest()


def multi_hash_seal(digest: str, salt: str = "research") -> str:
    """Simulate sealed lineage with secondary hash."""
    return hashlib.sha256(f"{digest}|{salt}".encode()).hexdigest()


class AuditLog:
    """Append-only hash chain with timestamps and optional sealed digest. Tampering changes the next digest."""

    def __init__(self) -> None:
        self.events: list[AuditEvent] = []
        self._previous = "GENESIS"

    def append(self, action: str, detail: str) -> AuditEvent:
        safe_detail = redact(detail)
        sequence = len(self.events) + 1
        ts = datetime.now(timezone.utc).isoformat()
        digest = hash_event(self._previous, sequence, action, safe_detail, ts)
        sealed = multi_hash_seal(digest)
        event = AuditEvent(sequence, action, safe_detail, self._previous, digest, sealed)
        self.events.append(event)
        self._previous = digest
        return event

    def verify(self) -> bool:
        previous = "GENESIS"
        for event in self.events:
            expected = hash_event(previous, event.sequence, event.action, event.detail, event.timestamp)
            if event.previous_hash != previous or event.digest != expected:
                return False
            previous = event.digest
        return True
