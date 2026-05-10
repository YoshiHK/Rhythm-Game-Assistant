from __future__ import annotations

from typing import Dict, Optional


def normalize_locale(
    requested_locale: Optional[str],
    *,
    locales_config: Dict,
    alias_config: Dict,
) -> Dict:
    """
    Normalize a requested locale into a canonical, supported locale.

    This function is wiring-only and non-semantic.
    It performs explicit table-based resolution with deterministic fallback.

    Inputs:
    - requested_locale: raw locale string from client (may be None)
    - locales_config: contents of translations/_meta/locales.json
    - alias_config: contents of translations/_meta/locale_aliases.json

    Returns a structured result dict:
    {
        "requested": <original input or None>,
        "resolved": <canonical supported locale>,
        "supported": <bool>,
        "fallback": <bool>,
        "fallback_reason": <str | None>,
        "base_locale": <base locale string>,
    }
    """

    # Defensive defaults
    requested = requested_locale.strip() if isinstance(requested_locale, str) else None

    supported_locales = set(
        locales_config.get("supported_locales", [])
        or locales_config.get("supportedLocales", [])
        or []
    )

    if not supported_locales:
        # Hard fallback: configuration error, but remain non-throwing
        return {
            "requested": requested,
            "resolved": None,
            "supported": False,
            "fallback": True,
            "fallback_reason": "no_supported_locales_configured",
            "base_locale": None,
        }

    # Determine base locale
    base_locale = (
        locales_config.get("base_locale")
        or locales_config.get("default_locale")
        or locales_config.get("root_locale")
        or next(iter(sorted(supported_locales)))
    )

    # Normalize aliases mapping
    aliases = alias_config.get("aliases", {}) if isinstance(alias_config, dict) else {}

    # Step 1: direct match
    if requested and requested in supported_locales:
        return {
            "requested": requested,
            "resolved": requested,
            "supported": True,
            "fallback": False,
            "fallback_reason": None,
            "base_locale": base_locale,
        }

    # Step 2: alias resolution
    if requested and requested in aliases:
        target = aliases.get(requested)
        if isinstance(target, str) and target in supported_locales:
            return {
                "requested": requested,
                "resolved": target,
                "supported": True,
                "fallback": True,
                "fallback_reason": "alias_resolution",
                "base_locale": base_locale,
            }

    # Step 3: fallback to base locale
    return {
        "requested": requested,
        "resolved": base_locale,
        "supported": False,
        "fallback": True,
        "fallback_reason": "base_locale_fallback",
        "base_locale": base_locale,
    }