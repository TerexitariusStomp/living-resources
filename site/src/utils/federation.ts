// SPDX-License-Identifier: AGPL-3.0-or-later
// Shared client-side fetch of the worker's GET /federation (5-min cached
// partner-network feed). Used by FedLive and LivePulse. Never throws —
// callers render honest fallbacks on failure.

export interface FedSource {
  name: string;
  devices?: number;
}
export interface FedDetection {
  species?: string;
  station?: string;
  at?: string;
}
export interface FederationFeed {
  sources?: FedSource[];
  latest_detections?: FedDetection[];
  generated_at?: string;
}

export async function fetchFederation(): Promise<FederationFeed | null> {
  try {
    const r = await fetch('/federation');
    if (!r.ok) return null;
    return (await r.json()) as FederationFeed;
  } catch {
    return null;
  }
}

export async function fetchPresence(): Promise<number | null> {
  try {
    const r = await fetch('/presence');
    const d = (await r.json()) as { listening?: number };
    return d.listening ?? null;
  } catch {
    return null;
  }
}
