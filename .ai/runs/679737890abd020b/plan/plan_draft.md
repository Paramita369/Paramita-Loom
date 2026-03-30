## Goal
統一 Paramita Loom 的 design tokens（border-radius、card backgrounds），修正 WCAG AA 色彩對比問題，為 GuideMetadata 加入 progressive disclosure，移除英文版 landing page 重複 card section，加入 tablet breakpoint，統一 ReviewBox 樣式。

## Motivation
Design critique 發現 6 個核心問題：(1) GuideMetadata 資訊過載無法收合 — 首次讀者被淹沒；(2) --loom-soft 色彩對比僅 3.2:1，未達 WCAG AA 4.5:1 標準；(3) 至少 6 種不同 border-radius 值缺乏系統性；(4) 英文版 Landing page "Reading order" 重複 "Approved batch" 的 3 張 cards（zh-hk 版不受影響，兩個 grid 內容不同）；(5) 只有 50rem 一個 breakpoint，tablet 體驗缺失；(6) ReviewBox background 不用 token。這些問題影響 accessibility compliance、visual consistency 和 usability。

## Affected Files
- `src/styles/custom.css` — design tokens 定義、border-radius 統一（限定範圍）、contrast 修正、tablet breakpoint
- `src/components/GuideMetadata.astro` — secondary sections 加入 `<details>` progressive disclosure
- `src/content/docs/index.mdx` — 移除重複 Reading order SectionCardGrid（僅英文版）
- `src/components/ReviewBox.astro` — background 改用 --loom-card token、加 accent border
- **不受影響**：`src/content/docs/zh-hk/index.mdx`（結構已正確，無重複問題）
- **不受影響**：`src/components/SectionCardGrid.astro`、`ProcessSteps.astro`、`BoundaryNote.astro`（只改 CSS token，不改 component code）

## Risk Areas
- **GuideMetadata `<details>` 元素**：Astro SSR 對 native `<details>` 應有良好支持（純 HTML），但需驗證 Starlight 沒有覆蓋其樣式
- **色彩對比連鎖影響**：修改 --loom-soft 會影響所有使用該 token 的元素；需在 light mode 和 dark mode 都驗證。具體配對：`--loom-soft` on `--sl-color-bg`（body text）、`--loom-soft` on `--loom-card`（card 內 meta text）、`--loom-soft` on `--loom-warm`（review box 內 text）
- **Landing page draft: true**：index.mdx 標記為 draft，修改後可在 dev mode 預覽但不進 production build
- **Border-radius 替換範圍**：只替換卡片/容器類圓角（見下方明確清單），不動 pill button (999px)、code inline (0.4rem)、label chips (999px)

## Rollback Strategy
每個 step 執行前，手動建立 git tag `pre-s{n}-679737890abd020b`。如任何 step 導致問題：
1. `git log --oneline` 找到對應 tag
2. `git revert HEAD` 回退該 step 的 commit
3. 各 step 改不同檔案區域，可獨立 revert

明確可執行的 revert 路徑：
- S1（CSS tokens）: `git revert` CSS commit — 所有 component 自動回到硬編碼值
- S2（contrast）: `git revert` — --loom-soft 回到原值
- S3（disclosure）: `git revert` — GuideMetadata 回到原本無收合狀態
- S4（landing dedup）: `git revert` — index.mdx 回到原本三個 section
- S5（breakpoint）: `git revert` — 移除 72rem media query
- S6（ReviewBox）: `git revert` — background 回到硬編碼值

## Open Questions
- `index.mdx` 的 `draft: true` 是否 intentional？如果是，S4 的修改對 production 無實際影響但改善 dev 體驗
- Dark mode 的 --loom-soft (#97a89d) 在深色背景上（#131814）對比度約 5.8:1，已達 AA，但如果覺得太亮可微調

## Out of Scope
- Content schema 變更（content.config.ts、publicProjectionMap.ts、chineseTemplateContract.ts）
- zh-hk/index.mdx 的結構（已確認無重複問題）
- 新增或移除 component
- Sidebar 結構調整
- Content 文字修改（只動 UI/layout，不動 editorial content）
- Astro/Starlight 版本升級
- pill button、code chip、label chip 的圓角（語義性圓角，不在統一範圍內）

## Test Coverage Plan
- **Build test**: `npm run build` 確認零 error
- **Visual regression**: dev server 啟動後截圖比對 landing page、guide page（含 GuideMetadata）
- **Accessibility contrast 矩陣**:
  - Light mode: --loom-soft (#566b5e) on --sl-color-bg (#f8f6f1) → 目標 ≥ 4.5:1
  - Light mode: --loom-soft on --loom-card (white 82%) → 驗證
  - Dark mode: --loom-soft (#97a89d) on --sl-color-bg (#131814) → 驗證 ≥ 4.5:1
  - Dark mode: --loom-soft on --loom-card (dark) → 驗證
- **Responsive**: 檢查 <50rem（mobile）、50-72rem（tablet）、>72rem（desktop）三個區間
- **Dark mode**: 切換 dark mode 確認色彩 token 正確套用
- **Progressive disclosure**: 確認 GuideMetadata secondary sections 預設收合，點擊可展開，無 console error
- **Landing page**: 確認英文版只有一個 card grid，zh-hk 版不受影響

## Implementation Steps (6 steps)

### S1: 統一 Design Tokens（custom.css only）
在 custom.css `:root` 加入三個 radius token：
- `--loom-radius-sm: 0.5rem`（inline code 等小元素保留原值不動）
- `--loom-radius-md: 1rem`（cards、notes、metadata panels）
- `--loom-radius-lg: 1.5rem`（sections、大容器）

**替換清單**（僅 custom.css）：
| Selector | 原值 | 新值 | 理由 |
|----------|------|------|------|
| `.loom-section` | 1.5rem | var(--loom-radius-lg) | 大容器 |
| `.loom-card` | 1.15rem | var(--loom-radius-md) | 卡片 |
| `.sl-link-card` | 1.25rem | var(--loom-radius-md) | 卡片 |
| `.loom-note` | 1rem | var(--loom-radius-md) | 卡片級 |
| `.loom-guide-metadata-card/panel/row` | 0.95rem | var(--loom-radius-md) | 卡片級 |
| `.loom-review-box` | 1rem | var(--loom-radius-md) | 卡片級 |
| `.loom-section` (mobile) | 1.2rem | var(--loom-radius-md) | mobile 容器 |

**不動的圓角**（例外清單）：
- `.hero .actions a` — 999px（pill button，語義性）
- `.sl-markdown-content code` — 0.4rem（inline code，語義性）
- `.loom-step-number` — 999px（circle badge）
- `.loom-labels li` — 999px（chip/tag）

統一 card background：`.loom-card` 從 `rgba(255,255,255,0.72)` 改為 `var(--loom-card)`。
移除 `.loom-section::before` wash overlay（測試後如層次感不足，可用 box-shadow 補償）。

### S2: 修正 Accessibility
Light mode：
- `--loom-soft` 從 `#6d7d74` 改為 `#566b5e`（on #f8f6f1 ≈ 4.6:1 ✓）
- `.loom-eyebrow` font-size 從 `0.8rem` → `0.85rem`
- `.loom-meta` font-size 從 `0.82rem` → `0.85rem`
- `.loom-guide-metadata-card dt` font-size 從 `0.8rem` → `0.85rem`

Dark mode：
- `--loom-soft` (#97a89d) on #131814 ≈ 5.8:1 — 已達 AA，不改
- 驗證 --loom-soft on --loom-card (dark) 對比度

### S3: GuideMetadata Progressive Disclosure
將 `metadataSections` 的每個 section 用 native `<details>` 包裹：
- `<summary>` 顯示 section title + intro（粗體 title + 灰色 intro）
- 預設關閉（無 `open` attribute）
- Primary rows 不變（始終可見）
- Projection section 始終可見
- Tags 始終可見
- 不需 JS hydration（純 HTML 行為）

### S4: 英文版 Landing Page 去重（僅 index.mdx）
移除 index.mdx 第二個 `<SectionCardGrid>`（Reading order, line 91-118）。
在 Approved batch 的 `intro` 加入簡短閱讀順序建議：
「These are the only public pages in this batch. Suggested reading order: start with the system boundary, then the builder workflow, then the verification loop.」

zh-hk/index.mdx **不做任何修改** — 兩個 SectionCardGrid 的內容不同（站點入口 vs 首批公開頁面），不構成重複。

### S5: Tablet Breakpoint
在 custom.css 加入 `@media (max-width: 72rem)` 斷點（放在現有 50rem 斷點之前）：
- `.loom-grid`: `grid-template-columns: repeat(2, 1fr)`
- `.loom-section`: padding 調整為 `1.4rem`
- `.loom-guide-metadata-primary`: `grid-template-columns: repeat(3, 1fr)`

### S6: ReviewBox 統一
- `.loom-review-box` background 從 `rgba(241, 235, 225, 0.48)` 改為 `var(--loom-card)`
- 加入左側 accent border：`border-left: 3px solid var(--sl-color-accent)`
- Dark mode 的 `.loom-review-box` background 也改為 `var(--loom-card)`
