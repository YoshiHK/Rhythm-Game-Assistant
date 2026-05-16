from __future__ import annotations

from typing import Any, Dict, Optional, List

from .fallback_rules import build_fallback_chain, validate_fallback_graph


def _lower(s: Optional[str]) -> Optional[str]:
    return s.lower() if isinstance(s, str) else None


def normalize_locale(
    requested_locale: Optional[str],
    *,
    locales_config: Dict[str, Any],
    alias_config: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Normalize a requested locale into a canonical, supported locale.

    Inputs:
    - requested_locale: raw user/client locale hint (may be None)
    - locales_config: dict containing:
        - base_locale: str
        - supported_locales: List[str]
        - fallbacks: Dict[str, List[str]]
    - alias_config: dict containing:
        - aliases: Dict[str, str]
      NOTE: keys are treated case-insensitively (lowercased)

    Output:
    {
      "requested_locale": <original>,
      "normalized_input": <lowered>,
      "canonical_locale": <resolved>,
      "is_supported": bool,
      "used_alias": bool,
      "alias_source": <key used or None>,
      "fallback_chain": [<canonical>, ...],
      "base_locale": <base>,
    }

    This function is presentation/routing-only and MUST NOT introduce semantics.
    """
    base_locale = str(locales_config.get("base_locale", "en-US"))
    supported_locales = locales_config.get("supported_locales", [])
    fallbacks = locales_config.get("fallbacks", {})

    if not isinstance(supported_locales, list) or not supported_locales:
        raise ValueError("locales_config.supported_locales must be a non-empty list")

    supported_locales = [str(x) for x in supported_locales]
    if not isinstance(fallbacks, dict):
        raise ValueError("locales_config.fallbacks must be a dict")

    # Validate fallback graph once per call (cheap + prevents drift)
    validate_fallback_graph(
        supported_locales=supported_locales,
        fallbacks={str(k): [str(x) for x in v] for k, v in fallbacks.items()},
        base_locale=base_locale,
    )

    aliases = alias_config.get("aliases", {})
    if not isinstance(aliases, dict):
        aliases = {}

    raw = requested_locale
    lowered = _lower(requested_locale)

    used_alias = False
    alias_source = None
    canonical = None

    # 1) If missing, default to base
    if lowered is None or lowered.strip() == "":
        canonical = base_locale
    else:
        # 2) Alias mapping (case-insensitive)
        if lowered in aliases:
            canonical = str(aliases[lowered])
            used_alias = True
            alias_source = lowered
        else:
            # 3) Try exact match as provided (case-sensitive canonical)
            #    Many inputs might be "en-US" already
            canonical = str(requested_locale)

    # 4) If still not supported, fall back to base
    if canonical not in supported_locales:
        canonical = base_locale

    chain = build_fallback_chain(
        canonical,
        fallbacks={str(k): [str(x) for x in v] for k, v in fallbacks.items()},
        base_locale=base_locale,
    )

    return {
        "requested_locale": raw,
        "normalized_input": lowered,
        "canonical_locale": canonical,
        "is_supported": canonical in supported_locales,
        "used_alias": used_alias,
        "alias_source": alias_source,
        "fallback_chain": chain,
        "base_locale": base_locale,
    }
