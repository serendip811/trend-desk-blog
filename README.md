# Trend Content Pipeline

Local pipeline for collecting trend sources, scoring ideas, and generating publish-ready content briefs.

## What it does

- Fetches RSS, JSON, or HTML-extracted trend feeds from configured sources
- Normalizes entries into one queue
- Scores entries by recency, source weight, keyword fit, and commercial intent
- Clusters similar headlines
- Writes:
  - `data/raw/*.json` snapshots
  - `outputs/trend-report.md`
  - `outputs/drafts/*.md`

This version is intentionally manual on the last step: you review the draft, edit tone, then post it yourself.

## Static site publishing

The blog itself now uses a small static-site generator:

- Site config lives in `content/site.json`
- Post sources live in `content/posts/*.html`
- `scripts/build_site.py` generates:
  - `site/index.html`
  - `site/archive.html`
  - `site/categories/*.html`
  - `site/posts/*.html`
  - `site/rss.xml`
  - `site/sitemap.xml`

### Writing a new post

1. Add a new file in `content/posts/<slug>.html`
2. Put front matter at the top
3. Write the article body as HTML below it

Example:

```html
---
title: 새 글 제목
description: 검색 결과와 공유 카드에 들어갈 설명
summary: 목록에 노출할 짧은 요약
deck: 본문 상단 리드 문장
date: 2026-03-19
category: digital-services
published: true
listed: true
rss: true
sitemap: true
---
<p>본문 시작</p>
```

Optional fields:

- `slug`: 비워두면 파일명에서 자동으로 가져옵니다.
- `page_title`, `breadcrumb_title`
- `updated_at`
- `feature_badge`
- `image`, `image_alt`
- `listed: false`: 본문은 생성하지만 홈/아카이브/카테고리 목록에서 숨깁니다.
- `rss: false`, `sitemap: false`: RSS 또는 사이트맵 제외가 필요할 때 사용합니다.

### Build and deploy flow

- Local preview or diff check: `python3 scripts/build_site.py`
- GitHub Pages deploy: push to `main`

The deploy workflow in `.github/workflows/deploy-pages.yml` now runs `python3 scripts/build_site.py` on GitHub Actions and then uploads the generated `site/` directory. That means:

1. Edit `content/` sources
2. Optionally run the build locally to inspect the generated output
3. Commit and push
4. GitHub Actions rebuilds and deploys the site

## Quick start

```bash
python3 pipeline.py run
```

Optional flags:

```bash
python3 pipeline.py run --limit 10 --config config/sources.json
```

## Source config

Edit `config/sources.json`.

The current default config is tuned for Korea-first information and lifestyle search discovery, not tech news or hotdeal feeds. It uses:

- Google Trends KR daily trending searches
- Google News KR searches around travel
- Google News KR searches around mobile plan pricing
- Google News KR searches around support programs and application topics
- Google News KR searches around Naver services
- Daum realtime interest signals from the homepage

Supported source types:

- `rss`
- `json`
- `html`

Each source supports:

- `name`: label used in reports
- `type`: `rss`, `json`, or `html`
- `url`: feed URL
- `weight`: source authority multiplier
- `topic_tags`: tags you care about
- `commercial_terms`: words that usually signal monetizable intent
- `active`: enable/disable source

## Output flow

1. Run pipeline
2. Open `outputs/trend-report.md`
3. Pick one of the generated files in `outputs/drafts/`
4. Rewrite or tighten the draft in your brand voice
5. Publish to Naver, Tistory, or anywhere else

## Notes

- This is a source-ingest and output system, not a browser auto-poster.
- RSS/JSON are easiest; HTML sources are more brittle but useful for communities and portal pages.
- You can later add LLM rewriting, Naver-ready formatting, or thumbnail generation.
