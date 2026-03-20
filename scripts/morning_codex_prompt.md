You are maintaining the Trend Desk blog in this repository.

Goal: complete one morning publishing cycle end to end.

Required workflow:
1. Run `python3 pipeline.py run --limit 12`.
2. Read `outputs/trend-report.md`, the generated drafts in `outputs/drafts/`, the writing rules in `README.md`, and the existing published sources in `content/posts/`.
3. Pick exactly 3 topic ideas that are timely, useful for Korean search intent, and not near-duplicates of already published posts.
4. For each chosen topic, verify the angle with current official or primary public sources before writing.
5. Create 3 new publish-ready posts in `content/posts/*.html` that follow the existing front matter and HTML structure used by this repo.
6. Keep claims conservative when dates, prices, benefits, or eligibility can change, and tell readers to re-check the latest official page when needed.
7. Include relevant source links in each post body and include internal links to `../categories/...` and `../archive.html`.
8. If a supporting image is clearly needed and you can create one safely inside this repo, add it under `site/assets/` and reference it from the post.
9. Run `python3 scripts/build_site.py` after writing.
10. Run `git diff --check`.

Quality rules:
- Do not hand-edit generated files in `site/` except through the normal build flow.
- Do not rewrite or delete existing posts unless a minimal related fix is truly necessary for the new posts.
- Avoid duplicate search intent across the 3 new posts.
- Prefer practical guide, checklist, comparison, or application-intent angles over pure news summaries.
- Use Korean copy for reader-facing content.
- If you create SVG or other original image assets, all visible text inside the image must be in Korean, not English.
- Match image copy to the article's Korean tone and make the image readable for Korean users without mixing in English headings.

Git rules:
- Do not commit.
- Do not push.

Before finishing, print a concise final note with:
- the 3 chosen topics
- the created `content/posts/*.html` paths
- whether `python3 scripts/build_site.py` passed
- whether `git diff --check` passed
