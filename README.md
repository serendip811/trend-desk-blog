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
