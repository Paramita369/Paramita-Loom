import { defineConfig } from 'astro/config';
import mdx from '@astrojs/mdx';
import sitemap from '@astrojs/sitemap';

import cloudflare from '@astrojs/cloudflare';

export default defineConfig({
  site: 'https://paramita-loom.pages.dev',

  i18n: {
    defaultLocale: 'zh-hk',
    locales: ['zh-hk', 'en'],
    routing: {
      prefixDefaultLocale: true,
    },
  },

  integrations: [mdx(), sitemap()],
  adapter: cloudflare(),
});