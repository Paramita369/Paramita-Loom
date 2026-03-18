import { defineConfig } from 'astro/config';
import mdx from '@astrojs/mdx';
import sitemap from '@astrojs/sitemap';
import starlight from '@astrojs/starlight';

const sidebar = [
  {
    label: 'Start Here',
    translations: {
      'zh-HK': '從這裡開始',
    },
    slug: 'start-here',
  },
  {
    label: 'Knowledge',
    translations: {
      'zh-HK': '知識',
    },
    autogenerate: { directory: 'knowledge' },
  },
  {
    label: 'Guides',
    translations: {
      'zh-HK': '指南',
    },
    autogenerate: { directory: 'guides' },
  },
  {
    label: 'Notes',
    translations: {
      'zh-HK': '筆記',
    },
    autogenerate: { directory: 'notes' },
  },
  {
    label: 'Reviews',
    translations: {
      'zh-HK': '評測',
    },
    autogenerate: { directory: 'reviews' },
  },
  {
    label: 'Resources',
    translations: {
      'zh-HK': '資源',
    },
    autogenerate: { directory: 'resources' },
  },
  {
    label: 'Support',
    translations: {
      'zh-HK': '支持',
    },
    autogenerate: { directory: 'support' },
  },
  {
    label: 'About / Now',
    translations: {
      'zh-HK': '關於 / 近況',
    },
    slug: 'about-now',
  },
];

export default defineConfig({
  site: 'https://loom.paramita.example',
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
      sidebar,
    }),
  ],
});
