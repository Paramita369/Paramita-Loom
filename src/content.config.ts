import { defineCollection } from 'astro:content';
import { z } from 'astro/zod';
import { docsLoader, i18nLoader } from '@astrojs/starlight/loaders';
import { docsSchema, i18nSchema } from '@astrojs/starlight/schema';

const CONTENT_TYPES = ['knowledge', 'guide', 'note', 'review', 'resource', 'support'] as const;
const STATUS_VALUES = ['draft', 'reviewed', 'publish_ready', 'published', 'archived'] as const;
const GUIDE_AUDIENCE_VALUES = ['end_user', 'operator', 'contributor'] as const;
const GUIDE_SURFACE_VALUES = ['official_cli', 'repo_self_hosted'] as const;
const VERIFICATION_CLASS_VALUES = [
  'researched_only',
  'dry_run_verified',
  'container_smoke_verified',
  'single_machine_verified',
  'multi_machine_verified',
  'stale_recheck_needed',
] as const;
const SHIPPING_LANE_VALUES = ['preview_only', 'shipping_candidate', 'shipping'] as const;

const guideTestedOnSchema = z.object({
  label: z.string().min(1).optional(),
  platform: z.string().min(1).optional(),
  host: z.string().min(1).optional(),
  host_os: z.string().min(1).optional(),
  image: z.string().min(1).optional(),
  runtime: z.string().min(1).optional(),
  verified_at: z.string().min(1),
  note: z.string().min(1).optional(),
}).refine((value) => Boolean(value.label || value.platform), {
  message: 'tested_on requires label or platform',
});

const guideEvidenceRefSchema = z.object({
  label: z.string().min(1).optional(),
  kind: z.string().min(1).optional(),
  path: z.string().min(1).optional(),
  target: z.string().min(1).optional(),
  note: z.string().min(1).optional(),
}).refine((value) => Boolean(value.label || value.kind) && Boolean(value.path || value.target), {
  message: 'evidence_refs requires label/kind and path/target',
});

export const collections = {
  docs: defineCollection({
    loader: docsLoader(),
    schema: docsSchema({
      extend: z.object({
        type: z.enum(CONTENT_TYPES).optional(),
        topic: z.string().min(1).optional(),
        status: z.enum(STATUS_VALUES).optional(),
        reviewedAt: z.string().min(1).optional(),
        guideVersion: z.string().min(1).optional(),
        verifiedAt: z.string().min(1).optional(),
        nextReviewAt: z.string().min(1).optional(),
        stalePolicyCode: z.enum(['remove_from_primary_entry_when_overdue']).optional(),
        stalePolicy: z.string().min(1).optional(),
        platforms: z.array(z.string().min(1)).optional(),
        audience: z.string().min(1).optional(),
        difficulty: z.string().min(1).optional(),
        guide_audience: z.enum(GUIDE_AUDIENCE_VALUES).optional(),
        guide_surface: z.enum(GUIDE_SURFACE_VALUES).optional(),
        verification_class: z.enum(VERIFICATION_CLASS_VALUES).optional(),
        tested_on: z.array(guideTestedOnSchema).optional(),
        evidence_refs: z.array(guideEvidenceRefSchema).optional(),
        known_limitations: z.array(z.string().min(1)).optional(),
        shipping_lane: z.enum(SHIPPING_LANE_VALUES).optional(),
        retest_trigger: z.array(z.string().min(1)).optional(),
        tags: z.array(z.string().min(1)).optional(),
        verificationLevelCode: z
          .enum(['doc_checked', 'local_verified', 'cross_platform_verified'])
          .optional(),
        updateTriggers: z.array(z.string().min(1)).optional(),
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
