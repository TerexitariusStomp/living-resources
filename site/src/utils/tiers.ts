// SPDX-License-Identifier: AGPL-3.0-or-later
// Single source for the site's plain-language claim tiers.
// Used wherever a claim needs a "how far along is it" chip.
import tiers from '~/data/tiers.json';

export type TierKey = keyof typeof tiers;
export { tiers };

/** Inline chip markup for use inside set:html descriptions. Live/federated
 * tiers get a pulsing dot. */
export const tierChip = (k: TierKey): string => {
  const t = tiers[k];
  const dot = 'pulse' in t && t.pulse ? '<span class="lc-live-dot mr-1"></span>' : '';
  return `<span class="inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${t.class}">${dot}${t.label}</span>`;
};
