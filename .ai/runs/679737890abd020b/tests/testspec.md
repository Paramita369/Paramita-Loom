# Test Specification: Paramita Loom UI Redesign

## Scope
This specification covers the UI changes described in the redesign plan, with emphasis on:
- design token unification for border radius and card surfaces
- WCAG AA contrast corrections for `--loom-soft`
- progressive disclosure behavior in `GuideMetadata`
- landing page deduplication on `src/content/docs/index.mdx`
- a new tablet breakpoint at `72rem`
- `ReviewBox` background and border updates
- regression checks for `SectionCardGrid`, `ProcessSteps`, and `BoundaryNote`

## Test Objectives
1. Confirm the site still builds cleanly after the CSS and component changes.
2. Verify the public UI uses the intended tokens consistently.
3. Verify accessibility improvements are real in both light and dark themes.
4. Verify the new disclosure pattern is usable without breaking server-rendered output.
5. Verify responsive layout behavior at mobile, tablet, and wide viewport sizes.
6. Verify no duplicate landing-page content remains.

## Test Environment
- Local development server
- Production build output
- Browser-based inspection with responsive viewport emulation
- Accessibility contrast checking using browser devtools or a comparable contrast tool

## Pages / Components to Verify
- `/`
- `/guides/*` pages that render `GuideMetadata`
- `/review/review-architecture/` and other pages using `ReviewBox`
- pages using `SectionCardGrid`, `ProcessSteps`, and `BoundaryNote`

## Test Coverage

### 1. Build and smoke validation
- Run the site build.
- Open the homepage and at least one guide page in the dev server.
- Confirm there are no runtime errors, broken imports, or render failures.

### 2. Token consistency
- Verify card and section surfaces use `var(--loom-card)` where the plan requires it.
- Verify the targeted components no longer rely on ad hoc border-radius values for card-like surfaces.
- Verify the new radius tokens are used consistently in `custom.css` and affected components.

### 3. Accessibility and contrast
- Verify `--loom-soft` in light mode meets WCAG AA contrast against its intended background context.
- Verify dark mode contrast does not regress below WCAG AA expectations.
- Verify eyebrow and metadata text remain readable after the font-size adjustments.

### 4. GuideMetadata progressive disclosure
- Verify secondary metadata sections are wrapped in native `<details>` elements.
- Verify these sections are collapsed by default.
- Verify clicking the `<summary>` opens and closes each section.
- Verify primary rows remain visible without interaction.
- Verify projection and tags remain visible when present.
- Verify there are no hydration, SSR, or console errors related to the disclosure pattern.

### 5. Landing page deduplication
- Verify the homepage contains only one approved batch card grid.
- Verify the former duplicated "Reading order" card section is removed.
- Verify the replacement guidance text is present in the approved batch intro.
- Verify all intended links remain accessible from the page.

### 6. Responsive behavior
- Verify mobile layout at widths below `50rem` still stacks cleanly.
- Verify tablet layout at widths up to and including `72rem` uses the new 2-column grid behavior.
- Verify wide screens above `72rem` retain the intended multi-column layout.
- Verify `GuideMetadata` primary and secondary grids adapt correctly at tablet width.

### 7. ReviewBox update
- Verify `ReviewBox` uses `var(--loom-card)` as its background.
- Verify the left accent border is present and uses `var(--sl-color-accent)`.
- Verify the box still reads clearly in dark mode.

### 8. Regression checks on related components
- Verify `SectionCardGrid`, `ProcessSteps`, and `BoundaryNote` still render correctly after radius token changes.
- Verify hover, spacing, and text hierarchy remain intact.
- Verify no unintended visual clipping or overflow appears from the token changes.

## Pass Criteria
The redesign is considered acceptable when all of the following are true:
- build completes successfully
- light-mode `--loom-soft` meets WCAG AA contrast
- dark mode does not introduce a contrast regression
- progressive disclosure works with native interaction and default collapsed state
- homepage duplication is removed
- tablet breakpoint behavior is correct at `72rem`
- `ReviewBox` uses the new tokenized surface and accent border
- related components remain visually stable

## Notes
- The landing page is marked `draft: true`, so this spec should validate both dev preview behavior and build behavior.
- If any token change causes broad visual drift, capture screenshots before deciding whether the drift is acceptable.
- Native `<details>` is preferred for disclosure because it avoids extra client-side complexity.
