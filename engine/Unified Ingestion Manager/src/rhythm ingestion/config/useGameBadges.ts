// useGameBadges.ts
// UI helper for games.json v3.
// Wiring-only: it does not generate tips and does not infer gameplay semantics.

export type Badge = { label: string; color: string; value: string };

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

// Hook-like helper (framework-agnostic)
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