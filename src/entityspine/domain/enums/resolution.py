"""
Resolution engine enums.

STDLIB ONLY - NO PYDANTIC.
"""

from enum import Enum


class ResolutionTier(int, Enum):
    """Storage tier that provided the resolution."""

    CACHE = -1
    TIER_0 = 0
    TIER_1 = 1
    TIER_2 = 2
    TIER_3 = 3


class ResolutionStatus(str, Enum):
    """Status of the resolution attempt."""

    FOUND = "found"
    NOT_FOUND = "not_found"
    AMBIGUOUS = "ambiguous"
    REDIRECTED = "redirected"
    ERROR = "error"


class ResolutionWarning(str, Enum):
    """Standard warning types for resolution results."""

    AS_OF_IGNORED = "as_of_ignored"
    TEMPORAL_NOT_SUPPORTED = "temporal_not_supported"
    MIC_NOT_SUPPORTED = "mic_not_supported"
    REDIRECT_FOLLOWED = "redirect_followed"
    MAX_REDIRECTS_REACHED = "max_redirects_reached"
    AMBIGUOUS_MATCH = "ambiguous_match"
    LOW_CONFIDENCE = "low_confidence"
    STALE_DATA = "stale_data"
    CACHE_HIT = "cache_hit"
    FUZZY_MATCH_ONLY = "fuzzy_match_only"


class MatchReason(str, Enum):
    """Why a resolution candidate matched the query."""

    # Exact identifier matches
    EXACT_CIK = "exact_cik"
    EXACT_LEI = "exact_lei"
    EXACT_ISIN = "exact_isin"
    EXACT_CUSIP = "exact_cusip"
    EXACT_FIGI = "exact_figi"
    EXACT_TICKER = "exact_ticker"

    # Name matches
    NAME_EXACT = "name_exact"
    NAME_FUZZY = "name_fuzzy"
    ALIAS_MATCH = "alias_match"

    # Derived matches
    REDIRECT_FOLLOWED = "redirect_followed"
    CROSS_REFERENCE = "cross_reference"

    # Ambiguous
    MULTIPLE_MATCHES = "multiple_matches"

    # Unknown
    UNKNOWN = "unknown"
