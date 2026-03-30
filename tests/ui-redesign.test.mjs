import assert from 'node:assert/strict';
import { after, test } from 'node:test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  canBindLocalPort,
  compositeColors,
  contrastRatio,
  countOccurrences,
  extractBlock,
  findRuleBlock,
  getDeclarationValue,
  parseColor,
  parseCssVariables,
  pathExists,
  readText,
  runNpmScript,
  startDevServer,
  stopDevServer,
  fetchHtml,
} from './helpers/site-test-utils.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT_DIR = path.resolve(__dirname, '..');

const CUSTOM_CSS_PATH = path.join(ROOT_DIR, 'src/styles/custom.css');
const ROOT_HOME_SOURCE_PATH = path.join(ROOT_DIR, 'src/content/docs/index.mdx');
const GUIDE_METADATA_PATH = path.join(ROOT_DIR, 'src/components/GuideMetadata.astro');
const REVIEW_BOX_PATH = path.join(ROOT_DIR, 'src/components/ReviewBox.astro');
const SECTION_CARD_GRID_PATH = path.join(ROOT_DIR, 'src/components/SectionCardGrid.astro');
const PROCESS_STEPS_PATH = path.join(ROOT_DIR, 'src/components/ProcessSteps.astro');
const BOUNDARY_NOTE_PATH = path.join(ROOT_DIR, 'src/components/BoundaryNote.astro');

const BUILT_ZH_HOME_PATH = path.join(ROOT_DIR, 'dist/zh-hk/index.html');
const BUILT_GUIDE_PATH = path.join(
  ROOT_DIR,
  'dist/zh-hk/guides/codex/how-chatgpt-and-codex-built-openclaw/index.html',
);
const BUILT_GUIDE_WITH_PROJECTION_PATH = path.join(
  ROOT_DIR,
  'dist/zh-hk/guides/openclaw/mac-install/index.html',
);
const BUILT_REVIEW_PATH = path.join(ROOT_DIR, 'dist/zh-hk/review/from-zero-to-live-preview/index.html');

const css = await readText(CUSTOM_CSS_PATH);
const homeSource = await readText(ROOT_HOME_SOURCE_PATH);
const guideMetadataSource = await readText(GUIDE_METADATA_PATH);
const reviewBoxSource = await readText(REVIEW_BOX_PATH);
const sectionCardGridSource = await readText(SECTION_CARD_GRID_PATH);
const processStepsSource = await readText(PROCESS_STEPS_PATH);
const boundaryNoteSource = await readText(BOUNDARY_NOTE_PATH);

let setupPromise;

async function ensureSetup() {
  if (!setupPromise) {
    setupPromise = (async () => {
      const build = runNpmScript(ROOT_DIR, 'build');
      const canBind = await canBindLocalPort();

      const builtHomeExists = await pathExists(BUILT_ZH_HOME_PATH);
      const builtGuideExists = await pathExists(BUILT_GUIDE_PATH);
      const builtProjectionGuideExists = await pathExists(BUILT_GUIDE_WITH_PROJECTION_PATH);
      const builtReviewExists = await pathExists(BUILT_REVIEW_PATH);

      const builtHomeHtml = builtHomeExists ? await readText(BUILT_ZH_HOME_PATH) : '';
      const builtGuideHtml = builtGuideExists ? await readText(BUILT_GUIDE_PATH) : '';
      const builtProjectionGuideHtml = builtProjectionGuideExists
        ? await readText(BUILT_GUIDE_WITH_PROJECTION_PATH)
        : '';
      const builtReviewHtml = builtReviewExists ? await readText(BUILT_REVIEW_PATH) : '';

      return {
        build,
        canBind,
        builtHomeExists,
        builtGuideExists,
        builtProjectionGuideExists,
        builtReviewExists,
        builtHomeHtml,
        builtGuideHtml,
        builtProjectionGuideHtml,
        builtReviewHtml,
      };
    })();
  }

  return setupPromise;
}

function getMetadataSection(html) {
  const match = html.match(/<section class="loom-section loom-guide-metadata">[\s\S]*?<\/section>/);
  return match ? match[0] : '';
}

after(async () => {
  if (!setupPromise) {
    return;
  }

  await setupPromise;
});

test('TS-01 build and smoke validation', async () => {
  const state = await ensureSetup();

  assert.equal(
    state.build.status,
    0,
    `Expected \`npm run build\` to succeed.\n${state.build.stdout}\n${state.build.stderr}`,
  );

  assert.equal(state.builtHomeExists, true, 'Expected the built zh-HK homepage to exist.');
  assert.equal(state.builtGuideExists, true, 'Expected the built guide page to exist.');
  assert.match(state.builtHomeHtml, /Paramita Loom/u);
  assert.match(state.builtGuideHtml, /ChatGPT/u);
  assert.doesNotMatch(state.builtHomeHtml, /(AstroError|Unhandled Runtime Error|500: Internal)/i);
  assert.doesNotMatch(state.builtGuideHtml, /(AstroError|Unhandled Runtime Error|500: Internal)/i);
});

test('TS-02 token consistency for radii and card surfaces', () => {
  const rootVariables = parseCssVariables(css, ':root');
  const radiusTokens = [...rootVariables.keys()].filter((name) => name.startsWith('--loom-radius-'));

  assert.ok(
    radiusTokens.length >= 2,
    'Expected shared `--loom-radius-*` tokens in `custom.css` for the redesign.',
  );

  const tokenizedSurfaceSelectors = [
    '.loom-section',
    '.loom-card',
    '.loom-guide-metadata-card',
    '.loom-guide-metadata-panel',
    '.loom-guide-metadata-row',
    '.loom-review-box',
  ];

  for (const selector of tokenizedSurfaceSelectors) {
    const block = findRuleBlock(css, selector);
    assert.ok(block, `Expected CSS rule for ${selector}.`);
    assert.match(
      getDeclarationValue(block, 'border-radius') ?? '',
      /var\(--loom-radius-/,
      `Expected ${selector} to use a shared radius token.`,
    );
  }

  for (const selector of ['.loom-section', '.loom-card', '.loom-review-box']) {
    const block = findRuleBlock(css, selector);
    assert.match(
      getDeclarationValue(block, 'background') ?? '',
      /var\(--loom-card\)/,
      `Expected ${selector} to use var(--loom-card).`,
    );
  }
});

test('TS-03 WCAG AA contrast for --loom-soft and metadata text', () => {
  const lightVariables = parseCssVariables(css, ':root');
  const darkVariables = parseCssVariables(css, ":root[data-theme='dark']");

  const lightSoft = parseColor(lightVariables.get('--loom-soft'));
  const lightCard = compositeColors(
    parseColor(lightVariables.get('--loom-card')),
    parseColor(lightVariables.get('--sl-color-bg')),
  );
  const darkSoft = parseColor(darkVariables.get('--loom-soft'));
  const darkCard = compositeColors(
    parseColor(darkVariables.get('--loom-card')),
    parseColor(darkVariables.get('--sl-color-bg')),
  );

  const lightContrast = contrastRatio(lightSoft, lightCard);
  const darkContrast = contrastRatio(darkSoft, darkCard);

  assert.ok(
    lightContrast >= 4.5,
    `Expected light-mode --loom-soft contrast to meet 4.5:1, received ${lightContrast.toFixed(2)}:1.`,
  );
  assert.ok(
    darkContrast >= 4.5,
    `Expected dark-mode --loom-soft contrast to meet 4.5:1, received ${darkContrast.toFixed(2)}:1.`,
  );

  const eyebrowBlock = findRuleBlock(css, '.loom-eyebrow');
  const metaBlock = findRuleBlock(css, '.loom-meta');

  assert.ok(eyebrowBlock, 'Expected `.loom-eyebrow` rule to exist.');
  assert.ok(metaBlock, 'Expected `.loom-meta` rule to exist.');
  assert.match(getDeclarationValue(eyebrowBlock, 'color') ?? '', /var\(--sl-color-text-accent\)/);
  assert.equal(getDeclarationValue(metaBlock, 'color'), 'var(--loom-soft)');
  assert.match(
    getDeclarationValue(metaBlock, 'font-size') ?? '',
    /0\.(8|82|84|85|86|88|9)\d*rem|1rem/,
    'Expected metadata text to remain at a readable size.',
  );
});

test('TS-04 GuideMetadata uses native progressive disclosure', async () => {
  const state = await ensureSetup();
  const metadataMarkup = getMetadataSection(state.builtGuideHtml);
  const projectionMarkup = getMetadataSection(state.builtProjectionGuideHtml);

  assert.match(
    guideMetadataSource,
    /<details[\s>]/,
    'Expected GuideMetadata to render secondary metadata inside native <details> elements.',
  );
  assert.match(
    guideMetadataSource,
    /<summary[\s>]/,
    'Expected GuideMetadata to render native <summary> controls.',
  );
  assert.match(metadataMarkup, /<details(?![^>]*\sopen\b)[^>]*>/i);
  assert.match(metadataMarkup, /<summary[^>]*>/i);
  assert.match(metadataMarkup, /指南對象/u);
  assert.match(metadataMarkup, /標籤/u);
  assert.match(projectionMarkup, /公開投影/u);
  assert.doesNotMatch(metadataMarkup, /(hydration|Hydration|console\.error|Unhandled Runtime Error)/);
});

test('TS-05 landing page deduplication and link access', async () => {
  const state = await ensureSetup();

  assert.equal(
    countOccurrences(homeSource, '<SectionCardGrid'),
    1,
    'Expected exactly one SectionCardGrid on `src/content/docs/index.mdx`.',
  );
  assert.doesNotMatch(homeSource, /eyebrow="Reading order"/);
  assert.match(homeSource, /Start with the first approved five pages/);

  const requiredLinks = [
    '/knowledge/openclaw/private-truth-to-public-projection/',
    '/guides/codex/how-chatgpt-and-codex-built-openclaw/',
    '/guides/mac/three-agent-codex-workflow/',
    '/review/from-zero-to-live-preview/',
    '/resources/ai-builder-stack/actual-openclaw-stack/',
  ];

  for (const href of requiredLinks) {
    assert.match(
      homeSource,
      new RegExp(`href:\\s*'${href.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}'`),
      `Expected homepage source to retain the link ${href}.`,
    );
  }

  assert.match(state.builtHomeHtml, /loom-grid/u);
});

test('TS-06 responsive behavior includes the 72rem tablet breakpoint', () => {
  const mobileBlock = extractBlock(css, '@media (max-width: 50rem)');
  const tabletBlock = extractBlock(css, '@media (max-width: 72rem)');

  const mobileGridBlock = findRuleBlock(css, '.loom-grid', { within: mobileBlock });
  const tabletGridBlock = findRuleBlock(css, '.loom-grid', { within: tabletBlock });
  const wideGridBlock = findRuleBlock(css, '.loom-grid');
  const tabletPrimaryBlock = findRuleBlock(css, '.loom-guide-metadata-primary', { within: tabletBlock });
  const tabletSecondaryBlock = findRuleBlock(css, '.loom-guide-metadata-secondary', { within: tabletBlock });

  assert.equal(getDeclarationValue(mobileGridBlock, 'grid-template-columns'), '1fr');
  assert.ok(tabletGridBlock, 'Expected `.loom-grid` to be adjusted inside the 72rem breakpoint.');
  assert.match(
    getDeclarationValue(tabletGridBlock, 'grid-template-columns') ?? '',
    /repeat\(2,\s*minmax\(0,\s*1fr\)\)|repeat\(2,/,
    'Expected tablet layout to use two columns.',
  );
  assert.match(
    getDeclarationValue(wideGridBlock, 'grid-template-columns') ?? '',
    /repeat\(auto-fit,\s*minmax\(/,
    'Expected wide layout to keep the multi-column auto-fit grid.',
  );
  assert.ok(tabletPrimaryBlock, 'Expected primary GuideMetadata grid rules at tablet width.');
  assert.ok(tabletSecondaryBlock, 'Expected secondary GuideMetadata grid rules at tablet width.');
});

test('TS-07 ReviewBox uses tokenized surface and accent border', async () => {
  const state = await ensureSetup();
  const reviewBoxBlock = findRuleBlock(css, '.loom-review-box');

  assert.match(reviewBoxSource, /class="loom-review-box"/);
  assert.ok(reviewBoxBlock, 'Expected `.loom-review-box` CSS rule to exist.');
  assert.match(getDeclarationValue(reviewBoxBlock, 'background') ?? '', /var\(--loom-card\)/);

  const accentBorder =
    getDeclarationValue(reviewBoxBlock, 'border-inline-start') ??
    getDeclarationValue(reviewBoxBlock, 'border-left');

  assert.match(
    accentBorder ?? '',
    /var\(--sl-color-accent\)/,
    'Expected ReviewBox to include a left accent border using the accent token.',
  );
  assert.doesNotMatch(state.builtReviewHtml, /(AstroError|Unhandled Runtime Error|500: Internal)/i);
});

test('TS-08 SectionCardGrid, ProcessSteps, and BoundaryNote regressions', async () => {
  const state = await ensureSetup();

  assert.match(sectionCardGridSource, /class="loom-card"/);
  assert.match(processStepsSource, /class="loom-step"/);
  assert.match(boundaryNoteSource, /class="loom-note"/);
  assert.match(state.builtHomeHtml, /class="loom-card"/);
  assert.match(state.builtHomeHtml, /class="loom-step"/);
  assert.match(state.builtHomeHtml, /class="loom-note"/);

  const cardHoverBlock = findRuleBlock(css, '.loom-card:hover');
  const noteBlock = findRuleBlock(css, '.loom-note');
  const stepBlock = findRuleBlock(css, '.loom-step');

  assert.ok(cardHoverBlock, 'Expected hover styling for SectionCardGrid cards.');
  assert.match(getDeclarationValue(cardHoverBlock, 'transform') ?? '', /translateY\(-2px\)/);
  assert.equal(getDeclarationValue(stepBlock, 'align-items'), 'start');
  assert.equal(getDeclarationValue(noteBlock, 'display'), 'grid');
});

test('TS-09 draft homepage remains previewable in development', async (t) => {
  const state = await ensureSetup();

  assert.match(homeSource, /draft:\s*true/);

  if (!state.canBind.ok) {
    t.skip(`Local dev preview cannot be validated in this environment: ${state.canBind.error?.message}`);
    return;
  }

  const server = await startDevServer(ROOT_DIR, 4321);

  try {
    const home = await fetchHtml(server, '/');
    assert.equal(home.status, 200, 'Expected the draft homepage to be reachable in local development.');
    assert.match(home.html, /From fragments to structure\. From review to sharing\./);
  } finally {
    await stopDevServer(server);
  }
});
