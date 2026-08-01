from __future__ import annotations

"""
chart_text_converter.py

Convert deterministic chart-like assets into canonical text representation.

Supported type_A inputs:
- .aff
- .sus
- .json
- .html / .htm
- .mht / .mhtml
- .txt

Design constraints
------------------
- deterministic
- read-only
- one-to-one handlers per extension
- no personalization/localization/tips storage
"""

from pathlib import Path
import hashlib
import html as html_lib
import json
import re
import email
from email import policy
from typing import Any, Dict, Optional

# --------------------------------------------------
# Asset model import
# --------------------------------------------------
try:
    from rhythm_ingestion.writers.models.chart_asset_model import (
        AssetSubtype,
        AssetType,
    )

except ImportError:
    try:
        from ..models.chart_asset_model import (
            AssetSubtype,
            AssetType,
        )

    except ImportError as e:
        raise RuntimeError(
            "Failed to import chart_asset_model from writers.models layer. "
            "Please verify package structure and PYTHONPATH."
        ) from e

CONVERSION_VERSION = 1
SUPPORTED_TEXT_EXTENSIONS = {".aff", ".sus", ".json", ".html", ".htm", ".mht", ".mhtml", ".txt"}
VIDEO_EXTENSIONS = {".mp4", ".webm", ".mkv", ".avi", ".mov"}


def _to_text(value: Any) -> str:
    return "" if value is None else str(value)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def classify_asset_subtype(path_or_ref: str | Path) -> str:
    s = _to_text(path_or_ref)
    if s.startswith("http://") or s.startswith("https://"):
        if "youtube.com" in s or "youtu.be" in s:
            return AssetSubtype.YOUTUBE.value
        return AssetSubtype.EXTERNAL_URL.value

    ext = Path(s).suffix.lower()
    if ext == ".aff":
        return AssetSubtype.AFF.value
    if ext == ".sus":
        return AssetSubtype.SUS.value
    if ext == ".json":
        return AssetSubtype.JSON.value
    if ext in {".html", ".htm"}:
        return AssetSubtype.HTML.value
    if ext in {".mht", ".mhtml"}:
        return AssetSubtype.MHT.value
    if ext == ".txt":
        return AssetSubtype.TEXT.value
    if ext in VIDEO_EXTENSIONS:
        return AssetSubtype.VIDEO_FILE.value
    return AssetSubtype.UNKNOWN.value


def classify_asset_type(path_or_ref: str | Path) -> str:
    subtype = classify_asset_subtype(path_or_ref)
    if subtype in {
        AssetSubtype.AFF.value,
        AssetSubtype.SUS.value,
        AssetSubtype.JSON.value,
        AssetSubtype.HTML.value,
        AssetSubtype.MHT.value,
        AssetSubtype.TEXT.value,
    }:
        return AssetType.TYPE_A.value
    return AssetType.TYPE_B.value


def _normalize_newlines(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text


def _strip_trailing_space(text: str) -> str:
    lines = [ln.rstrip() for ln in _normalize_newlines(text).split("\n")]
    return "\n".join(lines).strip() + "\n"


def _extract_text_from_html(raw_html: str) -> str:
    text = re.sub(r"<script.*?>.*?</script>", " ", raw_html, flags=re.I | re.S)
    text = re.sub(r"<style.*?>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html_lib.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text + "\n" if text else ""


def _convert_aff(path: Path) -> str:
    return _strip_trailing_space(path.read_text(encoding="utf-8", errors="replace"))


def _convert_sus(path: Path) -> str:
    return _strip_trailing_space(path.read_text(encoding="utf-8", errors="replace"))


def _convert_json(path: Path) -> str:
    raw = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    return json.dumps(raw, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def _convert_html(path: Path) -> str:
    raw_html = path.read_text(encoding="utf-8", errors="replace")
    return _extract_text_from_html(raw_html)


def _extract_best_part_from_mht(path: Path) -> str:
    msg = email.message_from_bytes(path.read_bytes(), policy=policy.default)
    html_part = None
    text_part = None

    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            try:
                payload = part.get_content()
            except Exception:
                payload = None
            if payload is None:
                continue
            if ctype == "text/html" and html_part is None:
                html_part = _to_text(payload)
            elif ctype == "text/plain" and text_part is None:
                text_part = _to_text(payload)
    else:
        ctype = msg.get_content_type()
        payload = msg.get_content()
        if ctype == "text/html":
            html_part = _to_text(payload)
        elif ctype == "text/plain":
            text_part = _to_text(payload)

    if html_part:
        return _extract_text_from_html(html_part)
    if text_part:
        return _strip_trailing_space(text_part)
    return ""


def _convert_mht(path: Path) -> str:
    return _extract_best_part_from_mht(path)


def _build_text_envelope(*, subtype: str, source_path: Path, content_text: str, metadata: Optional[Dict[str, Any]] = None) -> str:
    metadata = dict(metadata or {})
    header = [
        "# CHART_ASSET_TEXT v1",
        f"subtype={subtype}",
        f"source_file={source_path.name}",
    ]
    for k in sorted(metadata.keys()):
        if metadata[k] is not None:
            header.append(f"{k}={metadata[k]}")
    header_text = "\n".join(header)
    return f"{header_text}\n\n[CONTENT]\n{content_text}"


def convert_chart_file_to_text(path: Path, *, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    ext = path.suffix.lower()
    subtype = classify_asset_subtype(path)

    if ext == ".aff":
        body = _convert_aff(path)
    elif ext == ".sus":
        body = _convert_sus(path)
    elif ext == ".json":
        body = _convert_json(path)
    elif ext in {".html", ".htm"}:
        body = _convert_html(path)
    elif ext in {".mht", ".mhtml"}:
        body = _convert_mht(path)
    elif ext == ".txt":
        body = _strip_trailing_space(path.read_text(encoding="utf-8", errors="replace"))
    else:
        raise ValueError(f"unsupported type_A chart extension: {ext}")

    text_representation = _build_text_envelope(
        subtype=subtype,
        source_path=path,
        content_text=body,
        metadata=metadata,
    )

    return {
        "asset_type": AssetType.TYPE_A.value,
        "asset_subtype": subtype,
        "text_representation": text_representation,
        "content_sha256": sha256_text(text_representation),
        "conversion_version": CONVERSION_VERSION,
    }


def build_reference_asset(*, reference_url: str, subtype: Optional[str] = None) -> Dict[str, Any]:
    reference_url = _to_text(reference_url).strip()
    if not reference_url:
        raise ValueError("reference_url is required for type_B asset")
    subtype = subtype or classify_asset_subtype(reference_url)
    return {
        "asset_type": AssetType.TYPE_B.value,
        "asset_subtype": subtype,
        "text_representation": None,
        "reference_url": reference_url,
        "content_sha256": sha256_text(reference_url),
        "conversion_version": CONVERSION_VERSION,
    }


__all__ = [
    "CONVERSION_VERSION",
    "SUPPORTED_TEXT_EXTENSIONS",
    "VIDEO_EXTENSIONS",
    "classify_asset_type",
    "classify_asset_subtype",
    "convert_chart_file_to_text",
    "build_reference_asset",
    "sha256_text",
    "sha256_file",
]
