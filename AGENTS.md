# AGENTS.md — OC-Site

## Purpose
This repository is the public website layer for the OpenClaw ecosystem.

It is **not** the private knowledge vault.
It is **not** the source of truth for raw operating data.
It is a **public projection layer** for reviewed, publishable knowledge.

Primary public brand:
- Paramita Loom
- Chinese subtitle: 知識經緯

Recommended display:
- Paramita Loom · 知識經緯

## Core principles
1. Static-first
2. Content-first
3. Review-before-publish
4. Minimal complexity
5. Clear structure over visual novelty
6. Public-safe only
7. Do not invent hidden backend dependencies

## Repo role
This repo is responsible for:
- public site shell
- content presentation
- topic navigation
- publishable document rendering
- support / about / start-here pages
- static build and deployment preparation

This repo is **not** responsible for:
- private ingestion pipeline
- SQLite truth storage
- worker orchestration
- internal review queue logic
- private artifact storage
- raw transcript or raw vault handling

## Stack expectations
Prefer:
- Astro
- Starlight
- Markdown / MDX
- static site deployment

Do not introduce:
- heavy backend frameworks
- database runtime requirements
- unnecessary server-side state
- auth systems unless explicitly approved
- dynamic features that break static-first publishing

## Source of truth rules
- Public site content must come from reviewed, publishable bundles only.
- Do not treat draft notes, raw vault files, raw transcripts, or internal artifacts as publishable by default.
- Do not bypass review rules by directly exposing source materials.
- If a content field is missing or unclear, prefer to stop and report rather than guess.

## Content model rules
When working with content:
- preserve frontmatter consistency
- preserve slug stability once published
- preserve canonical URL behavior
- preserve topic / category structure
- keep metadata human-readable and machine-parseable
- do not silently rename fields used by build/rendering

If a schema change seems necessary:
- do not change it casually
- propose the smallest possible change
- explain impact on existing content
- add validation or regression coverage

## UX rules
The site should feel:
- calm
- structured
- readable
- trustworthy
- not noisy
- not overly commercial

Avoid:
- cluttered homepages
- excessive animations
- dark-pattern CTAs
- distracting carousels
- visual complexity that hurts reading

Prefer:
- clean navigation
- strong information hierarchy
- readable typography
- clear topic hubs
- obvious "Start Here" paths
- support / donation links that do not dominate content

## Branding rules
Use the brand consistently:
- Paramita Loom
- 知識經緯

Do not create alternate product names casually.
Do not split the public identity into multiple competing brands.
Do not make the site feel like a random blog if the intended role is a structured public knowledge layer.

## File ownership guidance
Agents working in this repo may usually edit:
- site config
- Astro config
- Starlight config
- content collections
- docs/content pages
- components
- layouts
- styles
- static assets
- build/test config for this repo

Agents should not edit:
- private pipeline repo files
- internal SQLite logic
- private vault files
- review-gate logic from the main OpenClaw repo
- raw ingestion code from the private system

## Safety and privacy rules
Never publish:
- private notes by accident
- internal-only URLs
- local filesystem paths
- raw transcripts unless explicitly marked publishable
- secrets, tokens, credentials, internal IDs
- private review comments
- unreviewed operational artifacts

If there is any doubt whether content is public-safe:
- stop
- flag the issue clearly
- ask for review through the normal project flow

## Change strategy
Make the smallest change that solves the problem.

Do not:
- refactor the whole site without approval
- redesign architecture casually
- rename many files for style only
- switch stack without approval
- add complexity to “future-proof” unnecessarily

Prefer:
- minimal, reversible patches
- clear diffs
- incremental improvements
- tests / validation when possible

## Testing and validation
Before declaring work complete, always try to validate as much as possible.

Preferred order:
1. install dependencies using the repo’s existing package manager
2. run local checks
3. run build
4. report any warnings or broken links
5. summarize risks

Package manager rule:
- if `pnpm-lock.yaml` exists, prefer `pnpm`
- else if `package-lock.json` exists, use `npm`
- else if `yarn.lock` exists, use `yarn`
- do not switch package manager casually

Typical commands (use only if scripts exist):
- install dependencies
- run dev preview
- run build
- run lint
- run content/schema validation
- run link checks

If a script does not exist:
- do not invent misleading success claims
- state clearly what could not be validated

## Required completion format
When finishing a task, return:
1. files changed
2. what was done
3. why this is minimal
4. validation performed
5. open risks
6. recommended next step

## Special rules for Codex agents
- Respect existing structure before creating new abstractions.
- Do not overwrite large sections of content without reason.
- Do not change frontmatter conventions unless explicitly requested.
- Do not fabricate missing content.
- If multiple approaches are possible, choose the one with the lowest architectural risk.
- If a task touches both site UX and content schema, separate the concerns clearly in the report.

## Default decision policy
If unclear, choose:
- simpler over clever
- static over dynamic
- readable over flashy
- reviewed over fast
- explicit over magical
- public-safe over convenient

## If blocked
If you are blocked by missing schema, missing reviewed content, or unclear publish rules:
- stop
- explain exactly what is missing
- do not patch around the uncertainty by guessing
