from __future__ import annotations
from typing import Dict, List, Optional


def normalize_locale(
    requested_locale: Optional[str],
    *,
    locales_config: Dict,
    alias_config: Dict,
) -> Dict:
    """
    Normalize an arbitrary locale input into a canonical, supported locale.

    Phase: 4.5 (Localization)
    Scope: Presentation-only
    Determinism: Required

    Inputs
    ------
    requested_locale:
        Raw locale input (e.g. "zh-CN", "EN_gb", "ja", None)

    locales_config:
        Parsed contents of translations/_meta/locales.json

    alias_config:
        Parsed contents of translations/_meta/locale_aliases.json

    Returns
    -------
    dict with keys:
        - requested_locale
        - normalized_locale
        - resolved_locale
        - fallback_chain
        - fallback_used
    """

    base_locale: str = locales_config["base_locale"]
    supported_locales: List[str] = locales_config["supported_locales"]
    fallbacks: Dict[str, List[str]] = locales_config.get("fallbacks", {})
    aliases: Dict[str, str] = alias_config.get("aliases", {})

    # --------------------------------------------------
    # Step 1: Sanitize input
    # --------------------------------------------------
    raw = (requested_locale or "").strip()
    sanitized = raw.replace("_", "-")
    lookup_key = sanitized.lower()

    # --------------------------------------------------
    # Step 2: Alias resolution
    # --------------------------------------------------
    normalized = aliases.get(lookup_key, sanitized)

    # --------------------------------------------------
    # Step 3: Canonical validation
    # --------------------------------------------------
    if normalized in supported_locales:
        return {
            "requested_locale": requested_locale,
            "normalized_locale": normalized,
            "resolved_locale": normalized,
            "fallback_chain": [],
            "fallback_used": False,
        }

    # --------------------------------------------------
    # Step 4: Fallback resolution (data-driven only)
    # --------------------------------------------------
    tried: List[str] = []
    queue: List[str] = fallbacks.get(normalized, [])

    for candidate in queue:
        tried.append(candidate)
        if candidate in supported_locales:
            return {
                "requested_locale": requested_locale,
                "normalized_locale": normalized,
                "resolved_locale": candidate,
                "fallback_chain": tried,
                "fallback_used": True,
            }

    # --------------------------------------------------
    # Step 5: Hard fallback to base locale
    # --------------------------------------------------
    return {
        "requested_locale": requested_locale,
        "normalized_locale": normalized,
        "resolved_locale": base_locale,
        "fallback_chain": tried + [base_locale],
        "fallback_used": True,
    }
