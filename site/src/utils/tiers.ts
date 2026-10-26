// SPDX-License-Identifier: AGPL-3.0-or-later
// Single source for the site's plain-language claim tiers.
// Used wherever a claim needs a "how much of this works today" chip.
import tiers from '~/data/tiers.json';

export type TierKey = keyof typeof tiers;
export { tiers };

/** Inline chip markup for use inside set:html descriptions. */
export const tierChip = (k: TierKey): string =>
  `<span class="inline-block rounded border px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${tiers[k].class}">${tiers[k].label}</span>`;
