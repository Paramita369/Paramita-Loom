/**
 * Routing utilities for Paramita Loom.
 * Replaces Starlight's slug/locale resolution.
 */

export interface RouteInfo {
  locale: 'zh-hk' | 'en';
  slug: string;
  url: string;
}

/**
 * Derive locale and slug from a content collection entry ID.
 * Entry IDs from glob loader look like: "zh-hk/guides/publishing-with-clarity.mdx"
 * or "guides/publishing-with-clarity.mdx" (root = English).
 */
export function deriveRoute(entryId: string): RouteInfo {
  // Strip file extension
  let slug = entryId.replace(/\.(mdx?|md)$/, '');

  // Detect locale
  let locale: 'zh-hk' | 'en' = 'en';
  if (slug.startsWith('zh-hk/')) {
    locale = 'zh-hk';
    slug = slug.slice('zh-hk/'.length);
  }

  // Strip trailing /index for index pages
  slug = slug.replace(/\/index$/, '');

  // Handle root index
  if (slug === 'index') {
    slug = '';
  }

  const url = slug ? `/${locale}/${slug}/` : `/${locale}/`;

  return { locale, slug, url };
}

/**
 * Get the category from a slug (first path segment).
 */
export function getCategory(slug: string): string {
  const firstSegment = slug.split('/')[0];
  return firstSegment || '';
}

/**
 * Category labels for navigation.
 */
export const categoryLabels: Record<string, Record<string, string>> = {
  'zh-hk': {
    knowledge: '知識',
    guides: '指南',
    review: '評測',
    resources: '資源',
    notes: '筆記',
  },
  en: {
    knowledge: 'Knowledge',
    guides: 'Guides',
    review: 'Reviews',
    resources: 'Resources',
    notes: 'Notes',
  },
};

export const navCategories = ['knowledge', 'guides', 'review', 'resources', 'notes'] as const;
