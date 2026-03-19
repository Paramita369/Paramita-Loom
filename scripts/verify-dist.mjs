import { access, readFile, readdir } from 'node:fs/promises';
import { constants } from 'node:fs';
import path from 'node:path';

const distDir = path.resolve('dist');
const site = 'https://paramita-loom.pages.dev';
const approvedSlugs = [
  'knowledge/openclaw/private-truth-to-public-projection',
  'guides/codex/how-chatgpt-and-codex-built-openclaw',
  'guides/mac/three-agent-codex-workflow',
  'review/from-zero-to-live-preview',
  'resources/ai-builder-stack/actual-openclaw-stack',
];
const requiredFiles = [
  '404.html',
  'robots.txt',
  'zh-hk/404/index.html',
  'zh-hk/index.html',
  'zh-hk/knowledge/index.html',
  'zh-hk/guides/index.html',
  'zh-hk/resources/index.html',
  'zh-hk/review/index.html',
  ...approvedSlugs.map((slug) => `zh-hk/${slug}/index.html`),
];
const approvedTitleChecks = {
  'zh-hk/guides/mac/three-agent-codex-workflow/index.html': {
    expected: ['Mac 上的 Codex 三人協作流程', 'Codex 三人協作流程', 'OpenClaw 如何整理成公開內容'],
    forbidden: ['Mac 上三人協作的 Codex 工作流程', 'Mac 上三人協作流程', 'private → public 閉環證明了什麼'],
  },
  'zh-hk/review/from-zero-to-live-preview/index.html': {
    expected: [
      '從空殼到公開預覽：OpenClaw 如何整理成可公開閱讀的內容',
      'Codex 三人協作流程',
      'OpenClaw 的 AI 開發工具組合',
    ],
    forbidden: [
      '從空殼到公開預覽：這條 private → public 閉環真正證明了什麼',
      '三人協作的 Codex 工作流程',
      'OpenClaw 的 AI Builder Stack',
    ],
  },
  'zh-hk/resources/ai-builder-stack/actual-openclaw-stack/index.html': {
    expected: ['OpenClaw 實際使用的 AI 開發工具組合', 'AI 開發工具組合', 'Codex 三人協作流程'],
    forbidden: ['OpenClaw 實際使用的 AI Builder Stack', '實際使用的 AI Builder Stack', '三人協作的 Codex 工作流程'],
  },
};
const guideMetadataChecks = {
  'zh-hk/guides/codex/how-chatgpt-and-codex-built-openclaw/index.html': {
    expected: [
      '指南資訊',
      '指南版本',
      '已驗證於',
      '下次覆核',
      '平台',
      '適合讀者',
      '難度',
      '標籤',
      '驗證層級',
      'v1',
      '2026-03-19',
      '2026-04-19',
      'ChatGPT、Codex、OpenClaw repo',
      '想把規劃與實作分開的讀者',
      '入門',
      '本地已驗證',
      'OpenClaw',
      'workflow',
      'review',
    ],
  },
  'zh-hk/guides/mac/three-agent-codex-workflow/index.html': {
    expected: [
      '指南資訊',
      '指南版本',
      '已驗證於',
      '下次覆核',
      '平台',
      '適合讀者',
      '難度',
      '標籤',
      '驗證層級',
      'v1',
      '2026-03-19',
      '2026-04-19',
      'Mac mini、Codex、OpenClaw repo',
      '需要單機多代理協作的人',
      '中階',
      '本地已驗證',
      'OpenClaw',
      'multi-agent',
      'workflow',
    ],
  },
};
const guideMetadataSourceChecks = {
  'src/content/docs/guides/codex/how-chatgpt-and-codex-built-openclaw.mdx': [
    'guideVersion:',
    'verifiedAt:',
    'nextReviewAt:',
    'platforms:',
    'audience:',
    'difficulty:',
    'tags:',
    'verificationLevel:',
    '<GuideMetadata />',
  ],
  'src/content/docs/zh-hk/guides/codex/how-chatgpt-and-codex-built-openclaw.mdx': [
    'guideVersion:',
    'verifiedAt:',
    'nextReviewAt:',
    'platforms:',
    'audience:',
    'difficulty:',
    'tags:',
    'verificationLevel:',
    '<GuideMetadata />',
  ],
  'src/content/docs/guides/mac/three-agent-codex-workflow.mdx': [
    'guideVersion:',
    'verifiedAt:',
    'nextReviewAt:',
    'platforms:',
    'audience:',
    'difficulty:',
    'tags:',
    'verificationLevel:',
    '<GuideMetadata />',
  ],
  'src/content/docs/zh-hk/guides/mac/three-agent-codex-workflow.mdx': [
    'guideVersion:',
    'verifiedAt:',
    'nextReviewAt:',
    'platforms:',
    'audience:',
    'difficulty:',
    'tags:',
    'verificationLevel:',
    '<GuideMetadata />',
  ],
};
const sectionReferenceChecks = {
  'zh-hk/index.html': {
    expected: [
      '先讀 OpenClaw',
      '查看首批指南',
      '編輯邏輯',
      '站點入口',
      '首批核准頁面',
      '知識',
      '指南',
      '評測',
      '資源',
      'OpenClaw 是什麼：系統真相與對外內容如何分工',
      '我如何用 ChatGPT 與 Codex 建立 OpenClaw',
      'Mac 上的 Codex 三人協作流程',
      '從空殼到公開預覽：OpenClaw 如何整理成可公開閱讀的內容',
      'OpenClaw 實際使用的 AI 開發工具組合',
    ],
    forbidden: [
      '/zh-hk/start-here/',
      '/zh-hk/notes/',
      '/zh-hk/support/',
      '/zh-hk/review/review-architecture/',
      '/zh-hk/knowledge/topics/',
      'Read OpenClaw',
      'Guide',
      'Review',
      'Resource',
      'Knowledge',
      'Approved batch',
      'Batch 1',
      'Reading order',
      'Phase 15',
      '評測寫作結構',
      '讀者支持',
      '從這裡開始',
    ],
  },
  'zh-hk/guides/index.html': {
    expected: ['Mac 上的 Codex 三人協作流程'],
    forbidden: ['Mac 上三人協作的 Codex 工作流程'],
  },
  'zh-hk/review/index.html': {
    expected: ['從空殼到公開預覽：OpenClaw 如何整理成可公開閱讀的內容'],
    forbidden: ['從空殼到公開預覽：這條 private → public 閉環真正證明了什麼'],
  },
  'zh-hk/resources/index.html': {
    expected: ['OpenClaw 實際使用的 AI 開發工具組合'],
    forbidden: ['OpenClaw 實際使用的 AI Builder Stack'],
  },
};
const allowedZhHkPages = new Set([
  '',
  '404',
  'guides',
  'knowledge',
  'resources',
  'review',
  ...approvedSlugs,
]);
const forbiddenZhHkPages = [
  'about-now',
  'guides/publishing-with-clarity',
  'knowledge/commonplace-ledger',
  'knowledge/topics',
  'knowledge/topics/fragments-and-structure',
  'notes',
  'notes/field-note-fragments',
  'resources/topic-mapping-kit',
  'review/review-architecture',
  'start-here',
  'support',
];
const forbiddenRootFiles = [
  'index.html',
  ...approvedSlugs.map((slug) => `${slug}/index.html`),
];
const sitemapCandidates = ['sitemap-index.xml', 'sitemap.xml', 'sitemap-0.xml'];
const requiredHeadings = [
  '先看結論',
  '為什麼值得關心',
  '核心模型',
  '例子與常見誤解',
  '相關頁面',
  '更新與覆核',
];
const forbiddenStrings = [
  'TL;DR',
  'Description',
  'Section Outline',
  'Core Points',
  'Tool Recommendation',
  'Public Article Contract v2',
  'Public Article Contract v3',
  'Disclosure',
  'Review note',
  'Related pages',
  'Why it matters',
  'Core model / main idea',
  'Examples / failure modes / usage',
];
const zhHkFallbackBanner = '此內容尚未提供繁體中文版本';

async function assertFile(relativePath) {
  await access(path.join(distDir, relativePath), constants.F_OK);
}

async function fileExists(relativePath) {
  try {
    await assertFile(relativePath);
    return true;
  } catch {
    return false;
  }
}

async function readDistFile(relativePath) {
  return readFile(path.join(distDir, relativePath), 'utf8');
}

async function readSourceFile(relativePath) {
  return readFile(path.resolve(relativePath), 'utf8');
}

function formatPagePath(relativePath) {
  return `/${relativePath.replace(/\/index\.html$/, '/').replace(/^index\.html$/, '')}`;
}

function normalizeBuiltZhHkPage(relativePath) {
  if (relativePath === 'index.html') {
    return '';
  }
  return relativePath.replace(/\/index\.html$/, '');
}

function zhHkLocFor(page) {
  if (page === '') {
    return `${site}/zh-hk/`;
  }
  return `${site}/zh-hk/${page}/`;
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function hasHeading(html, heading) {
  const headingPattern = new RegExp(`<h[1-6][^>]*>${escapeRegExp(heading)}</h[1-6]>`, 'i');
  return headingPattern.test(html);
}

async function verifyApprovedPage(relativePath, { extraHeadings = [] } = {}) {
  const html = await readDistFile(relativePath);
  const pagePath = formatPagePath(relativePath);
  const issues = [];
  const canonical = `${site}${pagePath}`;

  if (!html.includes(`rel="canonical" href="${canonical}"`)) {
    issues.push(`canonical mismatch for ${pagePath}`);
  }

  if (html.includes('rel="alternate" hreflang="en"')) {
    issues.push(`unexpected English hreflang alternate found in ${pagePath}`);
  }

  for (const heading of [...requiredHeadings, ...extraHeadings]) {
    if (!hasHeading(html, heading)) {
      issues.push(`missing required heading "${heading}" for ${pagePath}`);
    }
  }

  for (const forbidden of forbiddenStrings) {
    if (html.includes(forbidden)) {
      issues.push(`forbidden string "${forbidden}" found in ${pagePath}`);
    }
  }

  if (html.includes(zhHkFallbackBanner)) {
    issues.push(`zh-HK fallback banner found in ${pagePath}`);
  }

  if (html.includes('<starlight-lang-select')) {
    issues.push(`language selector should be hidden for ${pagePath}`);
  }

  if (html.includes('選擇語言')) {
    issues.push(`language selector label should not be visible for ${pagePath}`);
  }

  if (html.includes('/zh-hk/zh-hk/')) {
    issues.push(`duplicated zh-HK locale prefix found in ${pagePath}`);
  }

  return issues;
}

async function verifySearchExcludedPage(relativePath) {
  const html = await readDistFile(relativePath);
  const pagePath = formatPagePath(relativePath);
  const issues = [];

  if (html.includes('rel="alternate" hreflang="en"')) {
    issues.push(`unexpected English hreflang alternate found in ${pagePath}`);
  }

  if (html.includes('data-pagefind-body')) {
    issues.push(`pagefind body should be disabled for ${pagePath}`);
  }

  if (html.includes('<starlight-lang-select')) {
    issues.push(`language selector should be hidden for ${pagePath}`);
  }

  if (html.includes('選擇語言')) {
    issues.push(`language selector label should not be visible for ${pagePath}`);
  }

  return issues;
}

async function verifyTextSync(relativePath, { expected = [], forbidden = [] } = {}) {
  const html = await readDistFile(relativePath);
  const pagePath = formatPagePath(relativePath);
  const issues = [];

  for (const text of expected) {
    if (!html.includes(text)) {
      issues.push(`missing expected text "${text}" in ${pagePath}`);
    }
  }

  for (const text of forbidden) {
    if (html.includes(text)) {
      issues.push(`stale text "${text}" found in ${pagePath}`);
    }
  }

  return issues;
}

async function verifySourceTextSync(relativePath, expected = []) {
  const source = await readSourceFile(relativePath);
  const issues = [];

  for (const text of expected) {
    if (!source.includes(text)) {
      issues.push(`missing expected source text "${text}" in ${relativePath}`);
    }
  }

  return issues;
}

async function collectTextUnder(relativePath) {
  const contents = [];
  const queue = [path.join(distDir, relativePath)];

  while (queue.length > 0) {
    const currentDir = queue.pop();
    const entries = await readdir(currentDir, { withFileTypes: true });

    for (const entry of entries) {
      const absolutePath = path.join(currentDir, entry.name);
      if (entry.isDirectory()) {
        queue.push(absolutePath);
        continue;
      }

      const text = await readFile(absolutePath, 'utf8').catch(() => '');
      contents.push(text);
    }
  }

  return contents.join('\n');
}

async function listBuiltZhHkPages() {
  const pages = [];
  const queue = [path.join(distDir, 'zh-hk')];

  while (queue.length > 0) {
    const currentDir = queue.pop();
    const entries = await readdir(currentDir, { withFileTypes: true });

    for (const entry of entries) {
      const absolutePath = path.join(currentDir, entry.name);
      if (entry.isDirectory()) {
        queue.push(absolutePath);
        continue;
      }

      if (entry.name !== 'index.html') {
        continue;
      }

      const relativePath = path.relative(path.join(distDir, 'zh-hk'), absolutePath);
      pages.push(normalizeBuiltZhHkPage(relativePath));
    }
  }

  return pages.sort();
}

async function main() {
  const missing = [];
  const issues = [];

  for (const relativePath of requiredFiles) {
    if (!(await fileExists(relativePath))) {
      missing.push(relativePath);
    }
  }

  for (const relativePath of forbiddenRootFiles) {
    if (await fileExists(relativePath)) {
      issues.push(`unexpected root production file found: ${relativePath}`);
    }
  }

  const existingSitemaps = [];
  for (const candidate of sitemapCandidates) {
    if (await fileExists(candidate)) {
      existingSitemaps.push(candidate);
    }
  }

  if (existingSitemaps.length === 0) {
    missing.push('sitemap-index.xml | sitemap.xml | sitemap-0.xml');
  }

  if (missing.length === 0) {
    const builtZhHkPages = await listBuiltZhHkPages();

    for (const page of builtZhHkPages) {
      if (!allowedZhHkPages.has(page)) {
        issues.push(`unexpected zh-HK public page built: /zh-hk/${page === '' ? '' : `${page}/`}`);
      }
    }

    for (const page of forbiddenZhHkPages) {
      if (builtZhHkPages.includes(page)) {
        issues.push(`forbidden zh-HK public page still built: /zh-hk/${page}/`);
      }
    }

    for (const slug of approvedSlugs) {
      const extraHeadings = slug === 'resources/ai-builder-stack/actual-openclaw-stack'
        ? ['披露說明']
        : [];
      issues.push(...(await verifyApprovedPage(`zh-hk/${slug}/index.html`, { extraHeadings })));
    }

    issues.push(...(await verifySearchExcludedPage('zh-hk/404/index.html')));

    for (const [relativePath, rules] of Object.entries(approvedTitleChecks)) {
      issues.push(...(await verifyTextSync(relativePath, rules)));
    }

    for (const [relativePath, rules] of Object.entries(guideMetadataChecks)) {
      issues.push(...(await verifyTextSync(relativePath, rules)));
    }

    for (const [relativePath, expected] of Object.entries(guideMetadataSourceChecks)) {
      issues.push(...(await verifySourceTextSync(relativePath, expected)));
    }

    for (const [relativePath, rules] of Object.entries(sectionReferenceChecks)) {
      issues.push(...(await verifyTextSync(relativePath, rules)));
    }

    const robotsTxt = await readDistFile('robots.txt');
    if (robotsTxt.includes('loom.paramita.example')) {
      issues.push('dist/robots.txt still contains example domain');
    }
    if (!robotsTxt.includes(`Sitemap: ${site}/sitemap-index.xml`)) {
      issues.push('dist/robots.txt sitemap line does not match production domain');
    }

    const sitemapXml = (
      await Promise.all(existingSitemaps.map((candidate) => readDistFile(candidate)))
    ).join('\n');
    const allowedZhHkLocs = new Set([...allowedZhHkPages].map((page) => zhHkLocFor(page)));
    const allLocs = [...sitemapXml.matchAll(/<loc>(.*?)<\/loc>/g)].map((match) => match[1]);

    for (const slug of approvedSlugs) {
      const zhHkLoc = `${site}/zh-hk/${slug}/`;
      const rootLoc = `${site}/${slug}/`;
      if (!sitemapXml.includes(`<loc>${zhHkLoc}</loc>`)) {
        issues.push(`sitemap is missing zh-HK approved page ${zhHkLoc}`);
      }
      if (sitemapXml.includes(`<loc>${rootLoc}</loc>`)) {
        issues.push(`sitemap still exposes root locale page ${rootLoc}`);
      }
    }

    if (sitemapXml.includes(`<loc>${site}/</loc>`)) {
      issues.push('sitemap still exposes the root index route');
    }

    for (const loc of allLocs) {
      if (loc.startsWith(`${site}/zh-hk/`) && !allowedZhHkLocs.has(loc)) {
        issues.push(`sitemap still exposes non-approved zh-HK page ${loc}`);
      }
    }

    if (!(await fileExists('pagefind'))) {
      missing.push('pagefind');
    } else {
      const pagefindText = await collectTextUnder('pagefind');
      for (const page of forbiddenZhHkPages) {
        const pagePath = `/zh-hk/${page}/`;
        if (pagefindText.includes(pagePath)) {
          issues.push(`pagefind still indexes forbidden zh-HK page ${pagePath}`);
        }
      }
    }
  }

  if (missing.length > 0) {
    console.error('Dist verification failed. Missing expected files:');
    for (const entry of missing) {
      console.error(`- ${entry}`);
    }
    process.exit(1);
  }

  if (issues.length > 0) {
    console.error('Dist verification failed. Acceptance issues found:');
    for (const issue of issues) {
      console.error(`- ${issue}`);
    }
    process.exit(1);
  }

  console.log('Dist verification passed.');
  console.log('zh-HK approved pages, public-scope gating, hreflang gating, sitemap gating, and forbidden-term checks all passed.');
}

await main();
