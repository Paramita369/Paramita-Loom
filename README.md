# Paramita-Loom

Public projection shell for **Paramita Loom · 知識經緯** built with Astro + Starlight.

## What is here

- bilingual public-site shell with root English routes and `zh-hk` locale scaffolding
- branded homepage, section landing pages, topic-hub structure, and sample docs pages
- calm editorial styling that keeps support content present but separate from core reading flow
- static-first setup with MDX, sitemap generation, and CI build checks

## Contract status

- `src/content.config.ts` consumes the frozen approved public contract fields already in use by this repo
- this site remains a projection layer only and does not become a truth source

## Local development

```bash
npm install
npm run dev
npm run check
npm run build
npm run verify:dist
```

## Preview workflow

To reproduce the current public preview shape locally:

```bash
npm run preview:prepare
npm run preview
```

Then open `/zh-hk/`.

Current recorded preview proof:
[https://paramita-loom.pages.dev/zh-hk/](https://paramita-loom.pages.dev/zh-hk/)

## Structure

- `src/content/docs/` stores English docs routes and samples
- `src/content/docs/zh-hk/` stores Traditional Chinese locale pages
- `src/content/i18n/zh-HK.json` provides starter UI translations
- `src/components/` contains the small presentation components used by home and sample pages
- `.github/workflows/site.yml` runs install, type/content checks, build, dist verification, and sitemap sanity checks

## Deployment note

`astro.config.mjs` currently uses `https://loom.paramita.example` as a placeholder `site` URL so sitemap generation can run during development. Replace it with the canonical production domain before deployment.

## Known non-blocking risks

- `review/reviews` naming cleanup
- current non-blocking build warning
