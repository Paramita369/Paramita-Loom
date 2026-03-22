import {
  getChineseTemplateForbiddenPhrases,
  getChineseTemplateSections,
  type ChineseTemplateKey,
} from './chineseTemplateContract.ts';

export const PUBLIC_SITE_TYPES = ['knowledge', 'guide', 'note', 'review', 'resource', 'support'] as const;
export const CONTENT_FAMILIES = ['product', 'openclaw_related', 'religious_text', 'generic'] as const;
export const CONTENT_INTENTS = [
  'general_summary',
  'release_update',
  'intro',
  'deep_test',
  'compare',
  'how_to',
  'system_update',
  'workflow_explain',
  'text_explain',
] as const;
export const INSTRUCTION_MODES = ['none', 'tutorial'] as const;
export const CLAIM_REGIMES = [
  'verifiable_fact',
  'source_claim',
  'measured_test',
  'subjective_review',
  'market_hypothesis',
  'mixed',
] as const;
export const PROJECTION_CONFIDENCE_VALUES = ['low', 'medium', 'high'] as const;
export const PUBLICATION_STATE_VALUES = [
  'private_preview_candidate',
  'public_candidate',
  'preview_deployment_candidate',
  'publish_ready',
] as const;

export type PublicSiteType = (typeof PUBLIC_SITE_TYPES)[number];
export type ContentFamily = (typeof CONTENT_FAMILIES)[number];
export type ContentIntent = (typeof CONTENT_INTENTS)[number];
export type InstructionMode = (typeof INSTRUCTION_MODES)[number];
export type ClaimRegime = (typeof CLAIM_REGIMES)[number];
export type ProjectionConfidence = (typeof PROJECTION_CONFIDENCE_VALUES)[number];
export type PublicationState = (typeof PUBLICATION_STATE_VALUES)[number];

export interface FrozenProjectionInput {
  content_family?: string | null;
  content_intent?: string | null;
  instruction_mode?: string | null;
  claim_regime?: string | null;
  site_type_projection?: string | null;
  compat_primary_profile?: string | null;
  route_version?: string | null;
  route_origin?: string | null;
  recipe_key?: string | null;
  appendix_policy?: string | null;
  projection_confidence?: string | null;
  publication_state?: string | null;
  nav_hidden?: boolean | null;
  search_hidden?: boolean | null;
}

export interface FrozenProjectionResolution {
  routeSignature: string;
  routeVersion: string;
  routeOrigin: string;
  compatPrimaryProfile: string;
  contentFamily: ContentFamily | 'unknown';
  contentIntent: ContentIntent | 'general_summary';
  instructionMode: InstructionMode;
  claimRegime: ClaimRegime;
  siteTypeProjection: PublicSiteType | null;
  targetChineseTemplate: ChineseTemplateKey | null;
  requiredReaderSections: string[];
  forbiddenReaderPhrases: string[];
  projectionConfidence: ProjectionConfidence;
  publicationState: PublicationState;
  hiddenFromNav: boolean;
  hiddenFromSearch: boolean;
  requiresApproval: boolean;
  hintMatchesRoute: boolean;
  isWave1SupportedRoute: boolean;
}

type RouteEntry = {
  siteTypeProjection: PublicSiteType;
  targetChineseTemplate: ChineseTemplateKey;
  routeNote: string;
  forbiddenReaderPhrases: readonly string[];
};

const COMMON_ROUTE_FORBIDDEN = [
  'Knowledge Recommendation',
  'A/B/C/D/E',
  'Learning Points',
  '對 OpenClaw 的意義',
  'generic fallback',
  'raw subtitle fragments',
  'subtitle residue',
] as const;

const ROUTE_MATRIX: Record<string, RouteEntry> = {
  'product:intro': {
    siteTypeProjection: 'resource',
    targetChineseTemplate: 'resource',
    routeNote: '產品介紹頁以資源卡方式公開，保持清楚、短版、可掃讀。',
    forbiddenReaderPhrases: COMMON_ROUTE_FORBIDDEN,
  },
  'product:release_update': {
    siteTypeProjection: 'resource',
    targetChineseTemplate: 'resource',
    routeNote: '產品更新與 rumor analysis 以資源卡方式公開，避免 generic summary shell。',
    forbiddenReaderPhrases: COMMON_ROUTE_FORBIDDEN,
  },
  'product:deep_test': {
    siteTypeProjection: 'review',
    targetChineseTemplate: 'review',
    routeNote: '深測內容以評測卡方式公開，保留測試語氣與觀察分隔。',
    forbiddenReaderPhrases: COMMON_ROUTE_FORBIDDEN,
  },
  'product:compare': {
    siteTypeProjection: 'review',
    targetChineseTemplate: 'review',
    routeNote: '比較內容以評測卡方式公開，集中比較維度與結論。',
    forbiddenReaderPhrases: COMMON_ROUTE_FORBIDDEN,
  },
  'product:how_to:tutorial': {
    siteTypeProjection: 'guide',
    targetChineseTemplate: 'guide',
    routeNote: '教學內容以指南卡方式公開，重點放步驟與預期結果。',
    forbiddenReaderPhrases: COMMON_ROUTE_FORBIDDEN,
  },
  'openclaw_related:system_update': {
    siteTypeProjection: 'knowledge',
    targetChineseTemplate: 'knowledge',
    routeNote: '系統更新內容以知識卡方式公開，保留背景與核心解釋。',
    forbiddenReaderPhrases: COMMON_ROUTE_FORBIDDEN,
  },
  'openclaw_related:workflow_explain': {
    siteTypeProjection: 'knowledge',
    targetChineseTemplate: 'knowledge',
    routeNote: 'workflow 解釋以知識卡方式公開，聚焦概念與邊界。',
    forbiddenReaderPhrases: COMMON_ROUTE_FORBIDDEN,
  },
  'openclaw_related:how_to': {
    siteTypeProjection: 'guide',
    targetChineseTemplate: 'guide',
    routeNote: 'OpenClaw 操作教學以指南卡方式公開，保留步驟與下一步。',
    forbiddenReaderPhrases: COMMON_ROUTE_FORBIDDEN,
  },
  'religious_text:text_explain': {
    siteTypeProjection: 'knowledge',
    targetChineseTemplate: 'knowledge',
    routeNote: '宗教或文化解釋頁以知識卡方式公開，強制分隔來源聲稱與可驗證事實。',
    forbiddenReaderPhrases: COMMON_ROUTE_FORBIDDEN,
  },
  'generic:general_summary': {
    siteTypeProjection: 'note',
    targetChineseTemplate: 'note',
    routeNote: '泛用總結只保留為 note fallback，不得變成所有內容的主流外殼。',
    forbiddenReaderPhrases: COMMON_ROUTE_FORBIDDEN,
  },
} as const;

function normalizeLower(value: string | null | undefined) {
  return typeof value === 'string' ? value.trim().toLowerCase() : '';
}

function normalizePublicSiteType(value: string | null | undefined): PublicSiteType | null {
  const candidate = normalizeLower(value);

  return (PUBLIC_SITE_TYPES as readonly string[]).includes(candidate) ? (candidate as PublicSiteType) : null;
}

function normalizePublicationState(value: string | null | undefined): PublicationState {
  const candidate = normalizeLower(value);

  if ((PUBLICATION_STATE_VALUES as readonly string[]).includes(candidate)) {
    return candidate as PublicationState;
  }

  return 'publish_ready';
}

function normalizeProjectionConfidence(value: string | null | undefined): ProjectionConfidence {
  const candidate = normalizeLower(value);

  if ((PROJECTION_CONFIDENCE_VALUES as readonly string[]).includes(candidate)) {
    return candidate as ProjectionConfidence;
  }

  return 'medium';
}

function normalizeContentFamily(value: string | null | undefined): ContentFamily | 'unknown' {
  const candidate = normalizeLower(value);

  return (CONTENT_FAMILIES as readonly string[]).includes(candidate) ? (candidate as ContentFamily) : 'unknown';
}

function normalizeContentIntent(value: string | null | undefined): ContentIntent {
  const candidate = normalizeLower(value);

  return (CONTENT_INTENTS as readonly string[]).includes(candidate)
    ? (candidate as ContentIntent)
    : 'general_summary';
}

function normalizeInstructionMode(value: string | null | undefined): InstructionMode {
  const candidate = normalizeLower(value);

  return (INSTRUCTION_MODES as readonly string[]).includes(candidate) ? (candidate as InstructionMode) : 'none';
}

function normalizeClaimRegime(value: string | null | undefined): ClaimRegime {
  const candidate = normalizeLower(value);

  return (CLAIM_REGIMES as readonly string[]).includes(candidate) ? (candidate as ClaimRegime) : 'mixed';
}

export function makeRouteSignature(input: FrozenProjectionInput): string {
  const family = normalizeContentFamily(input.content_family);
  const intent = normalizeContentIntent(input.content_intent);
  const instruction = normalizeInstructionMode(input.instruction_mode);

  return instruction === 'tutorial' ? `${family}:${intent}:${instruction}` : `${family}:${intent}`;
}

function resolveRouteEntry(input: FrozenProjectionInput): RouteEntry | null {
  const routeSignature = makeRouteSignature(input);

  return ROUTE_MATRIX[routeSignature] ?? null;
}

export function resolvePublicProjection(input: FrozenProjectionInput): FrozenProjectionResolution {
  const routeSignature = makeRouteSignature(input);
  const routeEntry = resolveRouteEntry(input);
  const contentFamily = normalizeContentFamily(input.content_family);
  const contentIntent = normalizeContentIntent(input.content_intent);
  const instructionMode = normalizeInstructionMode(input.instruction_mode);
  const claimRegime = normalizeClaimRegime(input.claim_regime);
  const compatPrimaryProfile = input.compat_primary_profile?.trim() || 'generic_fallback';
  const routeVersion = input.route_version?.trim() || 'route_v2';
  const routeOrigin = input.route_origin?.trim() || 'compatibility_backfill';
  const publicationState = normalizePublicationState(input.publication_state);
  const projectionConfidence = normalizeProjectionConfidence(input.projection_confidence);
  const providedHint = normalizePublicSiteType(input.site_type_projection);
  const targetChineseTemplate = routeEntry?.targetChineseTemplate ?? null;
  const siteTypeProjection = routeEntry?.siteTypeProjection ?? null;
  let hintMatchesRoute = false;
  if (routeEntry) {
    hintMatchesRoute = providedHint === routeEntry.siteTypeProjection || !providedHint;
  }
  const requiredReaderSections = routeEntry ? getChineseTemplateSections(targetChineseTemplate) : [];
  const forbiddenReaderPhrases = routeEntry
    ? [
        ...getChineseTemplateForbiddenPhrases(targetChineseTemplate),
        ...routeEntry.forbiddenReaderPhrases,
      ]
    : [
        ...COMMON_ROUTE_FORBIDDEN,
        'unknown route',
        'unsupported public projection',
        'operator-only field',
      ];

  return {
    routeSignature,
    routeVersion,
    routeOrigin,
    compatPrimaryProfile,
    contentFamily,
    contentIntent,
    instructionMode,
    claimRegime,
    siteTypeProjection,
    targetChineseTemplate,
    requiredReaderSections,
    forbiddenReaderPhrases,
    projectionConfidence,
    publicationState,
    hiddenFromNav: publicationState !== 'publish_ready' || Boolean(input.nav_hidden),
    hiddenFromSearch: publicationState !== 'publish_ready' || Boolean(input.search_hidden),
    requiresApproval: publicationState !== 'publish_ready',
    hintMatchesRoute,
    isWave1SupportedRoute: Boolean(routeEntry) && contentFamily !== 'unknown',
  };
}

export function isWave1SupportedContentFamily(value: string | null | undefined): value is ContentFamily {
  return normalizeContentFamily(value) !== 'unknown';
}

export function getExpectedTemplateForRoute(input: FrozenProjectionInput): ChineseTemplateKey | null {
  return resolvePublicProjection(input).targetChineseTemplate;
}

export function getExpectedSiteTypeForRoute(input: FrozenProjectionInput): PublicSiteType | null {
  return resolvePublicProjection(input).siteTypeProjection;
}

export function getRouteForbiddenReaderPhrases(input: FrozenProjectionInput): string[] {
  return resolvePublicProjection(input).forbiddenReaderPhrases;
}

export function getRouteReaderSections(input: FrozenProjectionInput): string[] {
  return resolvePublicProjection(input).requiredReaderSections;
}

export function isPreviewHidden(input: FrozenProjectionInput): boolean {
  const projection = resolvePublicProjection(input);

  return projection.hiddenFromNav || projection.hiddenFromSearch;
}
