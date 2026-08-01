// index.ts (UMI Config Layer)
// --------------------------------------------------
// Unified entry point for UMI configuration layer
// --------------------------------------------------

/**
 * Purpose
 * -------
 * Provide a stable import surface for UI-level configuration utilities.
 *
 * Scope
 * -----
 * - Exposes badge mapping logic for games.json-derived UI status/capability rendering
 * - UI wiring only (no gameplay semantics)
 * - No dependency on Python config layer (games_loader.py)
 *
 * Notes
 * -----
 * - This is the canonical UI config barrel file
 * - Phase 7 (Python config) remains separate
 * - Matrix tooling reads badge domains from this file directly
 */

export type Badge = { label: string; color: string; value: string };

export type GameEntry = {
  game_id: string;
  display_name?: string;
  overall_status?: string;
  capabilities?: Record<string, string>;
};

export type GameBadges = {
  overall: Badge;
  capabilities: Record<string, Badge>;
};

// --------------------------------------------------
// Badge definitions (directly exported for matrix detection)
// --------------------------------------------------

export const STATUS_BADGES: Record<string, Omit<Badge, "value">> = {
  rulebook: { label: "Rulebook", color: "purple" },
  anchor: { label: "Anchor", color: "blue" },
  enabled: { label: "Supported", color: "green" },
  disabled: { label: "Disabled", color: "gray" },
  future: { label: "Coming Soon", color: "orange" },
};

export const CAPABILITY_BADGES: Record<string, Omit<Badge, "value">> = {
  rulebook: { label: "Rulebook", color: "purple" },
  anchor: { label: "Anchor", color: "blue" },
  enabled: { label: "Enabled", color: "green" },
  ready: { label: "Ready", color: "green-outline" },
  disabled: { label: "Disabled", color: "gray" },
  future: { label: "Planned", color: "orange" },
};

// --------------------------------------------------
// Helpers
// --------------------------------------------------

const normalizeStatus = (s: unknown): string => {
  if (typeof s !== "string") return "";
  return s.trim().toLowerCase();
};

export function getStatusBadge(overallStatus: unknown): Badge {
  const v = normalizeStatus(overallStatus);
  const base = STATUS_BADGES[v] ?? { label: "Unknown", color: "gray" };
  return { ...base, value: v || "unknown" };
}

export function getCapabilityBadge(capValue: unknown): Badge {
  const v = normalizeStatus(capValue);
  const base = CAPABILITY_BADGES[v] ?? { label: "Unknown", color: "gray" };
  return { ...base, value: v || "unknown" };
}

// --------------------------------------------------
// Hook-like helper (framework-agnostic)
// --------------------------------------------------

export function useGameBadges(
  game: GameEntry | null | undefined
): GameBadges {
  const overall = getStatusBadge(game?.overall_status);
  const caps: Record<string, Badge> = {};
  const rawCaps = game?.capabilities ?? {};

  for (const key of Object.keys(rawCaps)) {
    caps[key] = getCapabilityBadge(rawCaps[key]);
  }

  return { overall, capabilities: caps };
}