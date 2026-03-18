import { access } from 'node:fs/promises';
import { constants } from 'node:fs';
import path from 'node:path';

const distDir = path.resolve('dist');
const requiredFiles = [
  'index.html',
  'start-here/index.html',
  'support/index.html',
  'review/index.html',
  'review/review-architecture/index.html',
  'zh-hk/index.html',
  'zh-hk/start-here/index.html',
  'zh-hk/support/index.html',
  'zh-hk/review/index.html',
  'zh-hk/review/review-architecture/index.html',
];

const sitemapCandidates = ['sitemap-index.xml', 'sitemap.xml', 'sitemap-0.xml'];

async function assertFile(relativePath) {
  const absolutePath = path.join(distDir, relativePath);
  await access(absolutePath, constants.F_OK);
}

async function main() {
  const missing = [];

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

  if (missing.length > 0) {
    console.error('Dist verification failed. Missing expected files:');
    for (const entry of missing) {
      console.error(`- ${entry}`);
    }
    process.exit(1);
  }

  console.log('Dist verification passed.');
  console.log('Preview proof path remains reproducible at /zh-hk/.');
}

await main();
