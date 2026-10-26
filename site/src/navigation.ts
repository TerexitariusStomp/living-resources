import { getPermalink } from './utils/permalinks';

export const headerData = {
  links: [
    { text: 'How it works', href: getPermalink('/how-it-works') },
    { text: 'Is it real?', href: getPermalink('/science') },
    { text: 'Developers', href: getPermalink('/developers') },
  ],
  actions: [{ text: 'Join', href: getPermalink('/#join') }],
};

export const footerData = {
  links: [
    {
      title: 'The project',
      links: [
        { text: 'Home', href: getPermalink('/') },
        { text: 'How it works', href: getPermalink('/how-it-works') },
        { text: 'The science', href: getPermalink('/science') },
        { text: 'For developers', href: getPermalink('/developers') },
        { text: 'Pitch deck', href: '/treetable-deck.pdf' },
      ],
    },
    {
      title: 'Source',
      links: [
        { text: 'GitHub — living-resources', href: 'https://github.com/treetable/living-resources' },
        {
          text: 'Architecture map',
          href: 'https://github.com/treetable/living-resources/blob/main/docs/ARCHITECTURE.md',
        },
        {
          text: 'Claim tiers (SCIENCE.md)',
          href: 'https://github.com/treetable/living-resources/blob/main/docs/SCIENCE.md',
        },
      ],
    },
    {
      title: 'The commons',
      links: [
        { text: 'Receipt ledger', href: getPermalink('/receipts') },
        { text: 'Connectome API', href: getPermalink('/info') },
        { text: 'Join the waitlist', href: getPermalink('/#join') },
      ],
    },
  ],
  secondaryLinks: [
    { text: 'Privacy', href: getPermalink('/privacy') },
    { text: 'Credits & licenses', href: getPermalink('/credits') },
  ],
  socialLinks: [
    { ariaLabel: 'GitHub', icon: 'tabler:brand-github', href: 'https://github.com/treetable/living-resources' },
  ],
  footNote: `
    TREETABLE LLC · AGPL-3.0-or-later · Built on <a class="underline" href="https://github.com/arthelokyo/astrowind">AstroWind</a> (MIT) and open libraries — see <a class="underline" href="/credits">credits</a>.
  `,
};
