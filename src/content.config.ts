import { defineCollection } from 'astro:content';
import { z } from 'astro/zod';
import { docsLoader, i18nLoader } from '@astrojs/starlight/loaders';
import { docsSchema, i18nSchema } from '@astrojs/starlight/schema';

const CONTENT_TYPES = ['knowledge', 'guide', 'note', 'review', 'resource', 'support'] as const;
const STATUS_VALUES = ['draft', 'reviewed', 'publish_ready', 'published', 'archived'] as const;

export const collections = {
  docs: defineCollection({
    loader: docsLoader(),
    schema: docsSchema({
      extend: z.object({
        type: z.enum(CONTENT_TYPES).optional(),
        topic: z.string().min(1).optional(),
        status: z.enum(STATUS_VALUES).optional(),
        reviewedAt: z.string().min(1).optional(),
        related: z.array(z.string().min(1)).optional(),
        slug: z.string().min(1).optional(),
      }),
    }),
  }),
  i18n: defineCollection({
    loader: i18nLoader(),
    schema: i18nSchema(),
  }),
};
