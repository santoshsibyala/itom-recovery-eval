"""Heuristics for detecting permanent vs transient failures.

This module provides pattern-based detection to classify errors as either:
- Permanent: Won't succeed on retry (e.g., "not found", "unauthorized")
- Transient: May succeed on retry (e.g., "timeout", "rate limit")

The classification helps the LLM understand which failed attempts are
worth retrying with the same parameters vs. which need a different approach.
"""

from __future__ import annotations

import re

# Patterns that suggest permanent failures (won't succeed on retry)
# Split into three logical categories:
#   1. Resource doesn't exist / access denied
#   2. State conflicts — operation already done or logically impossible
#   3. Business rule violations — retrying with same args will always fail
PERMANENT_PATTERNS = [
    # --- Resource / Access ---
    r"not found",
    r"does not exist",
    r"invalid",
    r"unauthorized",
    r"forbidden",
    r"disabled",
    r"deprecated",
    r"removed",
    r"deleted",
    r"terminated",

    # --- Idempotent state conflicts (retrying the SAME call is pointless) ---
    r"already\s+\w+",           # "already suspended", "already cancelled", "already processed"
    r"already\s+been",          # "has already been activated"
    r"cannot\s+suspend\s+again",
    r"cannot\s+resume",         # "cannot resume — not suspended"
    r"concurrent\s+modification",
    r"conflict",                # "reservation conflict", "concurrent modification conflict"
    r"not\s+suspended",         # "line is not suspended — cannot resume"
    r"not\s+active",
    r"not\s+eligible",
    r"state\s+conflict",

    # --- Business rule / hard limit violations ---
    r"permanently",
    r"breakdown",
    r"broken",
    r"not supported",
    r"no longer available",
    r"cancelled",
    r"rejected",
    r"limit\s+exceeded",        # "data refuel limit exceeded", "task limit exceeded"
    r"maximum\s+\w+\s+limit",
    r"insufficient\s+(?!.*retry)",  # "insufficient funds" — but NOT "insufficient for retry"
    r"unavailable",             # kept from original (catches service-level unavailability)
]

# Patterns that suggest transient failures (may succeed on retry)
# NOTE: transient patterns take PRECEDENCE over permanent ones (checked first).
# Keep these precise — avoid broad terms that could match permanent state errors.
TRANSIENT_PATTERNS = [
    r"timeout",
    r"timed out",
    r"temporarily",
    r"rate.?limit",
    r"too many requests",
    r"busy",
    r"overloaded",
    r"retry",
    r"connection.?refused",
    r"connection.?reset",
    r"network",
    r"503",
    r"502",
    r"504",
    r"temporarily unavailable",  # more specific than just "unavailable"
    r"try again",
    r"gateway timeout",
    r"bad gateway",
]


def is_likely_permanent(error: str) -> bool:
    """
    We have received an error message from a tool call and are trying to decide whether it is a permanent error or a transient error. Knowing this will help the next step to decide whether to retry or not. 

    Your goals is to consider the given TRANSIENT_PATTERNS and PERMANENT_PATTERNS and decide given error message is permanent and transient error patterns.  Transient patterns take precedence (if both match, assumes transient).

    Args:
        error: Error message to analyze

    Returns:
        True if the error appears permanent (won't succeed on retry),
        False if transient or unknown (may succeed on retry)

    Example:
        >>> is_likely_permanent("Machine unavailable due to breakdown")
        True
        >>> is_likely_permanent("Request timed out, please retry")
        False
        >>> is_likely_permanent("Something went wrong")
        False
    """
    error_lower = error.lower()

    # Check for transient patterns first (they override permanent)
    for pattern in TRANSIENT_PATTERNS:
        if re.search(pattern, error_lower):
            return False

    # Check for permanent patterns
    for pattern in PERMANENT_PATTERNS:
        if re.search(pattern, error_lower):
            return True

    # Default: unknown, assume not permanent (allow retry)
    return False
