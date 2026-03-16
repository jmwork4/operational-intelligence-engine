"""Input and Output Policy Guards.

These guards run **before** a user query reaches the model (InputPolicyGuard)
and **after** the model produces a response (OutputPolicyGuard).  Each guard
returns a :class:`PolicyResult` indicating whether the content is allowed,
which violations were detected, and a normalised risk score (0 – 1).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from uuid import UUID

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class PolicyResult:
    """Outcome of a policy guard check."""

    allowed: bool
    violations: list[str] = field(default_factory=list)
    risk_score: float = 0.0


# ---------------------------------------------------------------------------
# Prompt injection detection patterns
# ---------------------------------------------------------------------------

_INJECTION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
        "Prompt injection: 'ignore previous instructions' pattern detected.",
    ),
    (
        re.compile(r"disregard\s+(all\s+)?(prior|previous|above)\s+", re.IGNORECASE),
        "Prompt injection: 'disregard prior' pattern detected.",
    ),
    (
        re.compile(r"(reveal|show|print|output)\s+(your\s+)?(system\s+prompt|instructions)", re.IGNORECASE),
        "Prompt injection: attempt to extract system prompt.",
    ),
    (
        re.compile(r"you\s+are\s+now\s+(a|an|in)\s+", re.IGNORECASE),
        "Prompt injection: role reassignment pattern detected.",
    ),
    (
        re.compile(r"(act|behave|pretend)\s+as\s+(if\s+)?(you\s+)?(are|were)\s+", re.IGNORECASE),
        "Prompt injection: persona override pattern detected.",
    ),
    (
        re.compile(r"\bDAN\b.*\bjailbreak\b", re.IGNORECASE),
        "Prompt injection: DAN / jailbreak pattern detected.",
    ),
    (
        re.compile(r"forget\s+(everything|all)\s+(you|about)", re.IGNORECASE),
        "Prompt injection: memory wipe pattern detected.",
    ),
    (
        re.compile(r"<\s*/?\s*system\s*>", re.IGNORECASE),
        "Prompt injection: raw <system> tag detected.",
    ),
]

# ---------------------------------------------------------------------------
# PII detection patterns (output guard)
# ---------------------------------------------------------------------------

_PII_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        "PII: Social Security Number pattern detected.",
    ),
    (
        re.compile(r"\b\d{9}\b"),
        "PII: Possible SSN (9 consecutive digits) detected.",
    ),
    (
        re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
        "PII: Credit card number pattern detected.",
    ),
    (
        re.compile(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        ),
        "PII: Email address detected in generated output.",
    ),
    (
        re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
        "PII: Phone number pattern detected.",
    ),
]


# ---------------------------------------------------------------------------
# InputPolicyGuard
# ---------------------------------------------------------------------------

class InputPolicyGuard:
    """Validates user queries before they are sent to a model.

    Checks performed:
    * Prompt injection detection (regex-based heuristic)
    * Tenant model permissions
    * Tool permissions
    * Sensitive document exposure markers
    """

    async def check(
        self,
        query: str,
        tenant_id: UUID,
        context: dict | None = None,
    ) -> PolicyResult:
        """Run all input policy checks and return a :class:`PolicyResult`."""
        violations: list[str] = []
        risk_score: float = 0.0
        ctx = context or {}

        # 1. Prompt injection detection ---------------------------------
        injection_violations = self._check_injection(query)
        if injection_violations:
            violations.extend(injection_violations)
            # Each injection pattern adds 0.3 risk, capped at 1.0.
            risk_score = min(1.0, risk_score + 0.3 * len(injection_violations))

        # 2. Tenant model permissions -----------------------------------
        requested_model = ctx.get("requested_model")
        if requested_model:
            allowed_models = ctx.get("tenant_allowed_models")
            if allowed_models is not None and requested_model not in allowed_models:
                violations.append(
                    f"Tenant {tenant_id} is not permitted to use model "
                    f"{requested_model!r}."
                )
                risk_score = min(1.0, risk_score + 0.4)

        # 3. Tool permissions -------------------------------------------
        requested_tools = ctx.get("requested_tools", [])
        allowed_tools = ctx.get("tenant_allowed_tools")
        if allowed_tools is not None:
            for tool in requested_tools:
                if tool not in allowed_tools:
                    violations.append(
                        f"Tenant {tenant_id} is not permitted to use tool "
                        f"{tool!r}."
                    )
                    risk_score = min(1.0, risk_score + 0.2)

        # 4. Sensitive document exposure --------------------------------
        doc_classifications = ctx.get("document_classifications", [])
        for classification in doc_classifications:
            if classification.get("sensitivity") in ("SECRET", "TOP_SECRET"):
                violations.append(
                    f"Document {classification.get('document_id', 'unknown')!r} "
                    f"has sensitivity level {classification['sensitivity']!r} "
                    f"and cannot be included in this context."
                )
                risk_score = min(1.0, risk_score + 0.5)

        allowed = len(violations) == 0
        return PolicyResult(
            allowed=allowed,
            violations=violations,
            risk_score=round(risk_score, 2),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _check_injection(text: str) -> list[str]:
        hits: list[str] = []
        for pattern, message in _INJECTION_PATTERNS:
            if pattern.search(text):
                hits.append(message)
        return hits


# ---------------------------------------------------------------------------
# OutputPolicyGuard
# ---------------------------------------------------------------------------

class OutputPolicyGuard:
    """Validates model-generated responses before they are returned to the user.

    Checks performed:
    * PII leakage detection (regex-based)
    * Policy violation keywords
    * Unsupported claims detection
    """

    # Phrases that indicate the model may be making unsupported claims.
    _UNSUPPORTED_CLAIM_MARKERS: list[str] = [
        "I guarantee",
        "this is guaranteed",
        "100% certain",
        "absolutely certain",
        "I promise",
        "legally binding",
    ]

    # Policy violation keywords that should not appear in responses.
    _POLICY_VIOLATION_KEYWORDS: list[str] = [
        "bypass security",
        "hack into",
        "exploit vulnerability",
        "unauthorized access",
    ]

    async def check(
        self,
        response: str,
        context: dict | None = None,
    ) -> PolicyResult:
        """Run all output policy checks and return a :class:`PolicyResult`."""
        violations: list[str] = []
        risk_score: float = 0.0

        # 1. PII leakage -----------------------------------------------
        pii_violations = self._check_pii(response)
        if pii_violations:
            violations.extend(pii_violations)
            risk_score = min(1.0, risk_score + 0.4 * len(pii_violations))

        # 2. Policy violation keywords ----------------------------------
        policy_violations = self._check_policy_keywords(response)
        if policy_violations:
            violations.extend(policy_violations)
            risk_score = min(1.0, risk_score + 0.3 * len(policy_violations))

        # 3. Unsupported claims -----------------------------------------
        claim_violations = self._check_unsupported_claims(response)
        if claim_violations:
            violations.extend(claim_violations)
            risk_score = min(1.0, risk_score + 0.15 * len(claim_violations))

        allowed = len(violations) == 0
        return PolicyResult(
            allowed=allowed,
            violations=violations,
            risk_score=round(min(1.0, risk_score), 2),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _check_pii(text: str) -> list[str]:
        hits: list[str] = []
        for pattern, message in _PII_PATTERNS:
            if pattern.search(text):
                hits.append(message)
        return hits

    def _check_policy_keywords(self, text: str) -> list[str]:
        lower = text.lower()
        return [
            f"Policy violation: response contains prohibited phrase {kw!r}."
            for kw in self._POLICY_VIOLATION_KEYWORDS
            if kw in lower
        ]

    def _check_unsupported_claims(self, text: str) -> list[str]:
        lower = text.lower()
        return [
            f"Unsupported claim: response contains {marker!r}."
            for marker in self._UNSUPPORTED_CLAIM_MARKERS
            if marker.lower() in lower
        ]
