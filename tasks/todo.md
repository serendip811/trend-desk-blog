# Todo

- [x] 정적 사이트의 현재 수동 퍼블리시 구조와 GitHub Pages 배포 방식을 확인
- [x] `content/site.json`과 `content/posts/*.html`을 단일 원본으로 두는 생성기 초안을 추가
- [x] 생성 스크립트를 실행해 `site/` 출력물을 재생성하고 오류를 수정
- [x] README에 글 작성, 빌드, 검수, 푸시 절차를 문서화
- [x] 생성 결과와 diff를 검증하고 운영 흐름을 최종 확인

## Notes

- 목표는 "글 원본 수정 1곳 + 빌드 1번"으로 홈, 글 목록, 카테고리, 글 본문, RSS, 사이트맵이 함께 갱신되게 만드는 것.
- GitHub Pages workflow는 이제 푸시 시점에 `python3 scripts/build_site.py`를 실행한 뒤 `site/`를 배포한다.
- `chatgpt-plan-guide-2026`는 중복 주제 글이라 본문은 유지하되 `listed: false`, `rss: false`, `sitemap: false`로 숨긴다.

## Review

- `content/site.json`과 `content/posts/*.html`을 단일 원본으로 두고 홈, 아카이브, 카테고리, 글 본문, RSS, 사이트맵을 `scripts/build_site.py`로 생성하는 흐름을 추가했다.
- 글 source에서 `slug`를 빠뜨려도 파일명으로 자동 보완되도록 생성기를 완화했다.
- GitHub Pages workflow가 푸시 시 `scripts/build_site.py`를 실행하도록 바꿔서 로컬 빌드를 강제하지 않게 정리했다.
- README에 새 글 작성 형식과 `content -> build -> push -> deploy` 절차를 문서화했다.
- Verification:
- `python3 scripts/build_site.py` passed.
- `git diff --check` passed.
- `chatgpt-plan-guide-2026`는 `site/posts/chatgpt-plan-guide-2026.html`만 남고 홈, 아카이브, 카테고리, RSS, 사이트맵에는 노출되지 않음을 `rg`로 확인했다.
