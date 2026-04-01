import { defineConfig } from 'astro/config';
import mdx from '@astrojs/mdx';
import sitemap from '@astrojs/sitemap';
import starlight from '@astrojs/starlight';

const sidebar = [
  {
    label: 'Knowledge',
    translations: { 'zh-HK': '知識' },
    autogenerate: { directory: 'knowledge' },
  },
  {
    label: 'Guides',
    translations: { 'zh-HK': '指南' },
    autogenerate: { directory: 'guides' },
  },
  {
    label: 'Reviews',
    translations: { 'zh-HK': '評測' },
    autogenerate: { directory: 'review' },
  },
  {
    label: 'Resources',
    translations: { 'zh-HK': '資源' },
    autogenerate: { directory: 'resources' },
  },
  {
    label: 'Notes',
    translations: { 'zh-HK': '筆記' },
    autogenerate: { directory: 'notes' },
  },
];

export default defineConfig({
  site: 'https://paramita-loom.pages.dev',
  integrations: [
    mdx(),
    sitemap(),
    starlight({
      title: 'Paramita Loom · 知識經緯',
      description: 'A bilingual knowledge shell that turns fragments into structure and review into sharing.',
      defaultLocale: 'root',
      expressiveCode: false,
      logo: {
        src: './src/assets/loom-mark.svg',
        alt: 'Paramita Loom mark',
      },
      locales: {
        root: {
          label: 'English',
          lang: 'en',
        },
        'zh-hk': {
          label: '繁體中文',
          lang: 'zh-HK',
        },
      },
      customCss: ['./src/styles/custom.css'],
      components: {
        Head: './src/components/starlight/Head.astro',
        LanguageSelect: './src/components/starlight/LanguageSelect.astro',
        FallbackContentNotice: './src/components/starlight/FallbackContentNotice.astro',
      },
      sidebar,
    }),
  ],
});
