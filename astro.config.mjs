import { defineConfig } from 'astro/config';
import mdx from '@astrojs/mdx';
import sitemap from '@astrojs/sitemap';
import starlight from '@astrojs/starlight';

const sidebar = [
  {
    label: 'Knowledge',
    translations: {
      'zh-HK': '知識',
    },
    items: [
      {
        label: '系統真相與對外內容',
        link: '/knowledge/openclaw/private-truth-to-public-projection/',
      },
    ],
  },
  {
    label: 'Guides',
    translations: {
      'zh-HK': '指南',
    },
    items: [
      {
        label: '用 ChatGPT 與 Codex 建立 OpenClaw',
        link: '/guides/codex/how-chatgpt-and-codex-built-openclaw/',
      },
      {
        label: 'Codex 三人協作流程',
        link: '/guides/mac/three-agent-codex-workflow/',
      },
    ],
  },
  {
    label: 'Reviews',
    translations: {
      'zh-HK': '評測',
    },
    items: [
      {
        label: '從空殼到公開預覽',
        link: '/review/from-zero-to-live-preview/',
      },
    ],
  },
  {
    label: 'Resources',
    translations: {
      'zh-HK': '資源',
    },
    items: [
      {
        label: 'AI 開發工具組合',
        link: '/resources/ai-builder-stack/actual-openclaw-stack/',
      },
    ],
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
      },
      sidebar,
    }),
  ],
});
