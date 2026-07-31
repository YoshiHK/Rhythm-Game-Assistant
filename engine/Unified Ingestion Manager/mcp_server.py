#!/usr/bin/env python3
"""
mcp_server.py

RGA MCP Adapter (stdio JSON-RPC)

Purpose:
- Provide a thin MCP-compatible adapter for VS Code / Copilot MCP clients.
- Keep the existing RGA FastAPI REST backend unchanged.
- Forward MCP tool calls to the existing REST endpoint:
    POST /api/v1/recommend

Important boundary:
- This file is wiring only.
- It does not modify Completed Phases 1–7.
- It does not change canonical_row, pattern/tag logic, tips generation,
  personalization, localization, or recommendation internals.

Recommended placement:
- Place this file next to main.py in the backend project root:
  ...\Github Repository\engine\Unified Ingestion Manager\Unified Ingestion Manager\mcp_server.py

Environment variables:
- RGA_REST_URL      Optional. Defaults to http://127.0.0.1:8000/api/v1/recommend
- SOFTR_API_TOKEN   Required. Bearer token expected by the FastAPI auth layer.

Protocol:
- Minimal stdio JSON-RPC MCP adapter.
- Supports:
    initialize
    tools/list
    tools/call
    notifications/initialized
"""

from __future__ import annotations

import json
import os
import sys
import traceback
import urllib.error
import urllib.request
from typing import Any, Dict, Optional


RGA_REST_URL = os.getenv(
    "RGA_REST_URL",
    "http://127.0.0.1:8000/api/v1/recommend",
)

SERVER_NAME = "rhythm-game-assistant"
SERVER_VERSION = "0.1.0"


# -----------------------------------------------------------------------------
# JSON-RPC helpers
# -----------------------------------------------------------------------------

def _write_message(message: Dict[str, Any]) -> None:
    """Write one JSON-RPC message as a single line to stdout."""
    sys.stdout.write(json.dumps(message, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _result(request_id: Any, result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": result,
    }


def _error(request_id: Any, code: int, message: str, data: Optional[Any] = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": code,
            "message": message,
        },
    }
    if data is not None:
        payload["error"]["data"] = data
    return payload


# -----------------------------------------------------------------------------
# REST forwarding
# -----------------------------------------------------------------------------

def _post_to_rga(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Forward a tool request to the existing RGA REST API."""
    token = os.getenv("SOFTR_API_TOKEN", "").strip()
    if not token:
        raise RuntimeError("SOFTR_API_TOKEN is not set for the MCP adapter process.")

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    request = urllib.request.Request(
        RGA_REST_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "ngrok-skip-browser-warning": "true",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read().decode("utf-8")
            if not raw:
                return {"ok": True, "status": response.status, "body": None}
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"RGA REST API returned HTTP {exc.code}: {raw}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach RGA REST API at {RGA_REST_URL}: {exc}") from exc


# -----------------------------------------------------------------------------
# Tool schemas
# -----------------------------------------------------------------------------

def _tools_list() -> Dict[str, Any]:
    return {
        "tools": [
            {
                "name": "recommend_song",
                "description": (
                    "Request an RGA song-level recommendation or song coaching response. "
                    "This forwards to the existing RGA REST API without modifying core phases."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "game_id": {
                            "type": "string",
                            "description": "Game identifier, for example proseka.",
                            "default": "proseka",
                        },
                        "song_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional song IDs. If omitted, caller may provide player signals.",
                        },
                        "locale": {
                            "type": "string",
                            "description": "Locale for localized output.",
                            "default": "zh-HK",
                        },
                        "max_items": {
                            "type": "integer",
                            "description": "Maximum recommendation items to return.",
                            "default": 1,
                        },
                        "player_signals": {
                            "type": "object",
                            "description": "Player signal object from profile / Softr form / MCP prompt.",
                        },
                        "preferences": {
                            "type": "object",
                            "description": "Optional preference object.",
                        },
                    },
                    "required": ["game_id"],
                },
            },
            {
                "name": "recommend_game",
                "description": (
                    "Request an RGA game-level recommendation. "
                    "This is the progression → game recommendation entry surface."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "locale": {
                            "type": "string",
                            "default": "zh-HK",
                        },
                        "max_items": {
                            "type": "integer",
                            "default": 3,
                        },
                        "player_profile": {
                            "type": "object",
                            "description": "Player profile or progression context.",
                        },
                        "player_signals": {
                            "type": "object",
                            "description": "Aggregated gameplay signals.",
                        },
                        "preferences": {
                            "type": "object",
                            "description": "Optional preference object.",
                        },
                    },
                },
            },
            {
                "name": "recommend_rga",
                "description": (
                    "Advanced raw RGA request. Accepts a full request body and forwards it to "
                    "POST /api/v1/recommend. Use this when you already know the RGA REST schema."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "request": {
                            "type": "object",
                            "description": "Full RGA REST request body.",
                        }
                    },
                    "required": ["request"],
                },
            },
        ]
    }


# -----------------------------------------------------------------------------
# Tool dispatch
# -----------------------------------------------------------------------------

def _tool_call(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    if name == "recommend_song":
        payload = {
            "mode": "song",
            "game_id": arguments.get("game_id", "proseka"),
            "song_ids": arguments.get("song_ids") or [],
            "locale": arguments.get("locale", "zh-HK"),
            "max_items": arguments.get("max_items", 1),
            "preferences": arguments.get("preferences") or {
                "variant": "expert",
                "allow_personalization": True,
            },
            "player_history": arguments.get("player_history") or {},
            "player_profile": arguments.get("player_profile") or {},
            "player_signals": arguments.get("player_signals") or {},
            "evidence": arguments.get("evidence") or {},
        }
    elif name == "recommend_game":
        payload = {
            "mode": "game",
            "locale": arguments.get("locale", "zh-HK"),
            "max_items": arguments.get("max_items", 3),
            "preferences": arguments.get("preferences") or {},
            "player_history": arguments.get("player_history") or {},
            "player_profile": arguments.get("player_profile") or {},
            "player_signals": arguments.get("player_signals") or {},
            "evidence": arguments.get("evidence") or {},
        }
    elif name == "recommend_rga":
        payload = arguments.get("request")
        if not isinstance(payload, dict):
            raise ValueError("recommend_rga requires arguments.request to be an object.")
    else:
        raise ValueError(f"Unknown tool: {name}")

    response = _post_to_rga(payload)

    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(response, ensure_ascii=False, indent=2),
            }
        ],
        "isError": False,
    }


# -----------------------------------------------------------------------------
# MCP request handling
# -----------------------------------------------------------------------------

def _handle_request(message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    method = message.get("method")
    request_id = message.get("id")
    params = message.get("params") or {}

    # Notifications do not require responses.
    if request_id is None:
        return None

    if method == "initialize":
        return _result(
            request_id,
            {
                "protocolVersion": "2024-11-05",
                "serverInfo": {
                    "name": SERVER_NAME,
                    "version": SERVER_VERSION,
                },
                "capabilities": {
                    "tools": {},
                },
            },
        )

    if method == "tools/list":
        return _result(request_id, _tools_list())

    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        try:
            result = _tool_call(str(name), arguments)
            return _result(request_id, result)
        except Exception as exc:
            return _error(
                request_id,
                -32000,
                str(exc),
                data={"traceback": traceback.format_exc()},
            )

    return _error(request_id, -32601, f"Method not found: {method}")


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
            response = _handle_request(message)
            if response is not None:
                _write_message(response)
        except Exception as exc:
            _write_message(
                _error(
                    None,
                    -32700,
                    f"Invalid request: {exc}",
                    data={"traceback": traceback.format_exc()},
                )
            )


if __name__ == "__main__":
    main()
