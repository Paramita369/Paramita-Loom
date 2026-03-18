import { access, readFile } from 'node:fs/promises';
import { constants } from 'node:fs';
import path from 'node:path';

const distDir = path.resolve('dist');
const site = 'https://paramita-loom.pages.dev';
const approvedSlugs = [
  'knowledge/openclaw/private-truth-to-public-projection',
  'guides/codex/how-chatgpt-and-codex-built-openclaw',
  'guides/mac/three-agent-codex-workflow',
  'review/phase15/from-zero-to-live-preview',
  'resources/ai-builder-stack/actual-openclaw-stack',
];
const requiredFiles = [
  'index.html',
  'start-here/index.html',
  'support/index.html',
  'review/index.html',
  'review/review-architecture/index.html',
  'robots.txt',
  ...approvedSlugs.map((slug) => `${slug}/index.html`),
  'zh-hk/index.html',
  'zh-hk/start-here/index.html',
  'zh-hk/support/index.html',
  'zh-hk/review/index.html',
  'zh-hk/review/review-architecture/index.html',
  ...approvedSlugs.map((slug) => `zh-hk/${slug}/index.html`),
];
const sitemapCandidates = ['sitemap-index.xml', 'sitemap.xml', 'sitemap-0.xml'];
const requiredAnchors = [
  'tldr',
  'why-it-matters',
  'core-model--main-idea',
  'examples--failure-modes--usage',
  'related-pages',
  'review-note',
];
const forbiddenHeadings = ['Description', 'Section Outline', 'Core Points', 'Tool Recommendation'];
const zhHkFallbackBanner = '此內容尚未提供繁體中文版本';

async function assertFile(relativePath) {
  const absolutePath = path.join(distDir, relativePath);
  await access(absolutePath, constants.F_OK);
}

async function readDistFile(relativePath) {
  return readFile(path.join(distDir, relativePath), 'utf8');
}

function formatPagePath(relativePath) {
  return `/${relativePath.replace(/\/index\.html$/, '/').replace(/^index\.html$/, '')}`;
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function hasHeading(html, heading) {
  const headingPattern = new RegExp(`<h[1-6][^>]*>${escapeRegExp(heading)}</h[1-6]>`, 'i');
  return headingPattern.test(html);
}

async function verifyApprovedPage(relativePath, { expectZhHk = false } = {}) {
  const html = await readDistFile(relativePath);
  const pagePath = formatPagePath(relativePath);
  const issues = [];

  const canonical = `${site}${pagePath}`;
  if (!html.includes(`rel="canonical" href="${canonical}"`)) {
    issues.push(`canonical mismatch for ${pagePath}`);
  }

  for (const anchor of requiredAnchors) {
    if (!html.includes(`id="${anchor}"`)) {
      issues.push(`missing required anchor "${anchor}" for ${pagePath}`);
    }
  }

  for (const heading of forbiddenHeadings) {
    if (hasHeading(html, heading)) {
      issues.push(`forbidden heading "${heading}" found in ${pagePath}`);
    }
  }

  if (expectZhHk && html.includes(zhHkFallbackBanner)) {
    issues.push(`zh-HK fallback banner found in ${pagePath}`);
  }

  return issues;
}

async function main() {
  const missing = [];
  const issues = [];

  for (const relativePath of requiredFiles) {
    try {
      await assertFile(relativePath);
    } catch {
      missing.push(relativePath);
    }
  }

  let hasSitemap = false;
  for (const candidate of sitemapCandidates) {
    try {
      await assertFile(candidate);
      hasSitemap = true;
      break;
    } catch {
      // Try the next sitemap file name.
    }
  }

  if (!hasSitemap) {
    missing.push('sitemap-index.xml | sitemap.xml | sitemap-0.xml');
  }

  if (missing.length === 0) {
    for (const slug of approvedSlugs) {
      issues.push(...(await verifyApprovedPage(`${slug}/index.html`)));
      issues.push(...(await verifyApprovedPage(`zh-hk/${slug}/index.html`, { expectZhHk: true })));
    }

    const robotsTxt = await readDistFile('robots.txt');
    if (robotsTxt.includes('loom.paramita.example')) {
      issues.push('dist/robots.txt still contains example domain');
    }
    if (!robotsTxt.includes(`Sitemap: ${site}/sitemap-index.xml`)) {
      issues.push('dist/robots.txt sitemap line does not match production domain');
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
  console.log('Approved root + zh-HK pages, canonical metadata, anchors, headings, and robots.txt all passed.');
}

await main();
