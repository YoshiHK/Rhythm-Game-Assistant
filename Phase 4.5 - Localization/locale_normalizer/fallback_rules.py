from __future__ import annotations

from typing import Dict, List, Set


def build_fallback_chain(
    locale: str,
    *,
    fallbacks: Dict[str, List[str]],
    base_locale: str,
) -> List[str]:
    """
    Return a deterministic fallback chain for `locale`.

    Rules:
    - Chain starts with `locale`
    - Then appends fallbacks[locale] in order (if present)
    - Continue until base_locale is reached or no further fallback
    - Prevent cycles (stop and raise ValueError)
    - Ensure base_locale appears at the end if reachable

    Example:
    locale=zh-Hant-HK
    fallbacks={"zh-Hant-HK": ["zh-Hant-TW", "en-US"], "zh-Hant-TW": ["en-US"]}
    base_locale=en-US
    => ["zh-Hant-HK", "zh-Hant-TW", "en-US"]
    """
    chain: List[str] = []
    seen: Set[str] = set()

    cur = locale
    while True:
        if cur in seen:
            raise ValueError(f"Fallback cycle detected at '{cur}' in chain={chain}")
        seen.add(cur)
        chain.append(cur)

        if cur == base_locale:
            break

        nxts = fallbacks.get(cur, [])
        if not nxts:
            # No more fallbacks declared; stop.
            break

        # Deterministic: pick the first declared fallback as the next hop,
        # but also allow the chain to include intermediate hops by walking sequentially:
        # We choose the first hop; if later hops exist, they can be reached via that hop's fallbacks
        # OR directly if the first hop doesn't lead to base.
        # To preserve the user's declared order, we try each in order until one progresses.
        progressed = False
        for candidate in nxts:
            if candidate not in seen:
                cur = candidate
                progressed = True
                break
        if not progressed:
            # all candidates already seen -> cycle-like situation
            raise ValueError(f"Fallback cycle detected via candidates={nxts} chain={chain}")

    return chain


def validate_fallback_graph(
    *,
    supported_locales: List[str],
    fallbacks: Dict[str, List[str]],
    base_locale: str,
) -> None:
    """
    Validate fallback graph constraints:
    - base_locale must be in supported_locales
    - every locale in supported_locales must have a fallback chain that terminates
      (either at base_locale or at a leaf)
    - no cycles in fallback resolution
    """
    if base_locale not in supported_locales:
        raise ValueError(f"base_locale '{base_locale}' must be in supported_locales")

    supported_set = set(supported_locales)

    # validate that all fallback references are known locales
    for src, dsts in fallbacks.items():
        if src not in supported_set:
            # allowed but suspicious; keep strict to avoid drift
            raise ValueError(f"fallbacks contains unknown source locale '{src}'")
        if not isinstance(dsts, list):
            raise ValueError(f"fallbacks['{src}'] must be a list")
        for d in dsts:
            if d not in supported_set:
                raise ValueError(f"fallbacks['{src}'] references unknown locale '{d}'")

    # validate each locale has no cycles
    for loc in supported_locales:
        _ = build_fallback_chain(loc, fallbacks=fallbacks, base_locale=base_locale)