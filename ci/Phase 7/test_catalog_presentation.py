# ci/test_catalog_presentation.py

from rhythm_recommendation.phase7.catalog_merge import (
    resolve_display_name_from_merge,
)

def test_locale_alias_and_fallback_chain():
    display_node = {
        "default": "Project SEKAI",
        "i18n": {
            "en": "Project SEKAI (EN)",
            "en-GB": "Project SEKAI (UK)",
            "ja": "プロジェクトセカイ",
            "zh": "世界計畫",
            "zh-Hans": "世界计划（简体）",
            "zh-Hant": "世界計畫（繁體）",
            "zh-Hant-HK": "世界計畫（香港）",
        },
    }

    registry_name = "Project SEKAI (Registry)"

    locale_aliases = {
        "en": "en-US",
        "en-us": "en-US",
        "en-gb": "en-GB",
        "zh": "zh-Hans",
        "zh-cn": "zh-Hans",
        "zh-sg": "zh-Hans",
        "zh-hk": "zh-Hant-HK",
        "zh-hant-hk": "zh-Hant-HK",
        "zh-tw": "zh-Hant-TW",
        "zh-hant": "zh-Hant-TW",
        "ja": "ja-JP",
        "ja-jp": "ja-JP",
    }

    cases = [
        ("en", "Project SEKAI (EN)"),
        ("en-US", "Project SEKAI (EN)"),
        ("en-GB", "Project SEKAI (UK)"),
        ("ja", "プロジェクトセカイ"),
        ("ja-JP", "プロジェクトセカイ"),
        ("zh", "世界计划（简体）"),
        ("zh-CN", "世界计划（简体）"),
        ("zh-HK", "世界計畫（香港）"),
        ("zh-Hant-HK", "世界計畫（香港）"),
        ("fr-FR", "Project SEKAI"),
        ("", "Project SEKAI"),
    ]

    for locale, expected in cases:
        result = resolve_display_name_from_merge(
            registry_name=registry_name,
            display_node=display_node,
            locale=locale,
            locale_aliases=locale_aliases,
        )
        assert result == expected, f"Locale {locale!r} resolved to {result!r}, expected {expected!r}"
