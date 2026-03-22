export const CHINESE_TEMPLATE_KEYS = ['guide', 'resource', 'review', 'knowledge', 'note'] as const;

export type ChineseTemplateKey = (typeof CHINESE_TEMPLATE_KEYS)[number];

export interface ChineseTemplateContract {
  key: ChineseTemplateKey;
  title: string;
  sections: readonly string[];
  readerOnlyForbidden: readonly string[];
}

const COMMON_READER_FORBIDDEN = [
  'Knowledge Recommendation',
  'A/B/C/D/E',
  'Learning Points',
  '對 OpenClaw 的意義',
  'generic fallback',
  'raw subtitle',
  'transcript residue',
] as const;

export const CHINESE_TEMPLATE_CONTRACTS: Record<ChineseTemplateKey, ChineseTemplateContract> = {
  guide: {
    key: 'guide',
    title: '指南',
    sections: ['先看結論', '適合誰', '開始前準備', '步驟', '預期結果', '常見錯誤', '下一步'],
    readerOnlyForbidden: COMMON_READER_FORBIDDEN,
  },
  resource: {
    key: 'resource',
    title: '資源',
    sections: ['這是什麼', '適合誰', '核心特點', '限制', '替代方案', '結論'],
    readerOnlyForbidden: COMMON_READER_FORBIDDEN,
  },
  review: {
    key: 'review',
    title: '評測',
    sections: ['測試目的', '測試環境', '觀察結果', '與宣稱對照', 'verdict', '更新觸發條件'],
    readerOnlyForbidden: COMMON_READER_FORBIDDEN,
  },
  knowledge: {
    key: 'knowledge',
    title: '知識',
    sections: ['這是什麼內容', '背景', '核心解釋', '來源聲稱 vs 可驗證事實', '延伸閱讀'],
    readerOnlyForbidden: COMMON_READER_FORBIDDEN,
  },
  note: {
    key: 'note',
    title: '筆記',
    sections: ['這篇在講什麼', '重點', '值得記低的地方', '限制'],
    readerOnlyForbidden: COMMON_READER_FORBIDDEN,
  },
};

export function isChineseTemplateKey(value: string | null | undefined): value is ChineseTemplateKey {
  return Boolean(value && CHINESE_TEMPLATE_KEYS.includes(value as ChineseTemplateKey));
}

export function getChineseTemplateContract(
  value: string | null | undefined,
): ChineseTemplateContract | null {
  if (!isChineseTemplateKey(value)) {
    return null;
  }

  return CHINESE_TEMPLATE_CONTRACTS[value];
}

export function getChineseTemplateSections(value: string | null | undefined): string[] {
  return [...(getChineseTemplateContract(value)?.sections ?? [])];
}

export function getChineseTemplateForbiddenPhrases(value: string | null | undefined): string[] {
  return [...(getChineseTemplateContract(value)?.readerOnlyForbidden ?? [])];
}
