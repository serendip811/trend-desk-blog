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

## Current Task

- [x] 파이프라인 실행 방식과 소스 설정 확인
- [x] `pipeline.py`를 실행해 최신 리포트와 초안 후보 생성
- [x] 결과를 검토해 지금 쓰기 좋은 주제 추천

## Current Review

- `python3 pipeline.py run --limit 8`를 실행해 `data/raw/entries-20260319-220908.json`, `outputs/trend-report.md`, `outputs/drafts/*.md`를 생성했다.
- 샌드박스 네트워크 제한 때문에 첫 실행은 실패했고, 네트워크 권한으로 재실행해 총 384건 수집, 341건 필터링 결과를 얻었다.
- 점수만 보면 `KT엠모바일 취약계층 전용 요금제`, `여행가는 봄`, `국민연금 첫 가입 지원금`, `청년월세 지원`이 상위권이었다.
- 실제 블로그 주제로는 반복 노출 빈도와 검색형 확장성을 같이 봤을 때 `여행가는 봄 혜택 정리`가 가장 균형이 좋고, 정책형 글로는 `청년월세 지원 신청 정리`가 바로 쓰기 좋다.

## Parallel Draft Task

- [x] 세 주제를 병렬 에이전트로 분리해 초안 작성
- [x] 여행, 청년월세, KT엠모바일 글을 `content/posts/`에 실제 반영
- [x] 여행 카테고리를 공개 상태로 전환
- [x] 생성 스크립트를 다시 실행해 `site/` 출력물을 검증

## Parallel Draft Review

- `spring-travel-benefits-2026`, `youth-rent-support-checklist-2026`, `ktm-mobile-plan-guide-2026` 글을 추가했다.
- 에이전트 초안은 그대로 넣지 않고, 링크 형식과 사실 단정 표현을 메인에서 다시 정리해 현재 사이트 포맷에 맞게 다듬었다.
- 여행 카테고리는 `coming_soon: false`로 전환했고 카테고리 인덱스에도 실제 글 수가 반영됐다.
- 청년월세 글은 2024년 신청 공지와 2025년 복지서비스 안내책자 사이의 지원 기간 표현 차이를 함께 적어 최신 공고 재확인을 강조했다.
- Verification:
- `python3 scripts/build_site.py` passed.
- `git diff --check` passed.
- 새 글 3개가 홈, 아카이브, 각 카테고리, RSS, 사이트맵에 모두 반영됐음을 `rg`로 확인했다.

## Full Review Task

- [x] 전체 글 목록과 공개 상태 확인
- [x] 글별 병렬 에이전트 리뷰 완료
- [x] 에이전트 수정 결과를 통합 검토하고 필요한 보정 반영
- [x] 전체 사이트 재생성 및 노출 검증

## Full Review Notes

- 공개 글 5개와 비공개 글 1개를 글별 병렬 에이전트로 재검토했다.
- ChatGPT 가격 글은 2026-03-19 기준 공식 가격/도움말로 갱신했고, 비교용 SVG도 최신 플랜 구간에 맞게 보강했다.
- 숨김 ChatGPT 글은 가격 비교문과 각도를 분리해 `구독 전환 체크리스트`로 재작성했고 `listed: false`는 유지했다.
- 교육급여 글은 2026-03-02 교육부 보도자료와 복지로·교육비 원클릭·교육급여 바우처 공식 링크 기준으로 다시 정리했다.
- 청년월세 글과 여행 글, KT엠모바일 글은 공식 링크 중심으로 다시 쓰고 설명용 SVG 이미지를 추가했다.
- Verification:
- `python3 scripts/build_site.py` passed.
- `git diff --check` passed.
- 공개 글에서 내부 제작 문구는 제거됐고, 남은 `초안` 표현은 ChatGPT 활용 예시 문맥임을 확인했다.
- `listed: true` 공개 글 중 `image:`가 빠진 글은 없음을 확인했다.

## Current Task

- [x] 이번 요청의 SEO 블로그 패키지 작성 계획 수립
- [x] `여행가는 봄`용 한국어 SEO 패키지 초안 작성
- [x] 결과를 `tasks/todo.md`에 검토 메모로 남기기

## Current Review

- 이번 초안은 `travel` 카테고리용으로 정리했고, 검색 의도는 "여행가는 봄 혜택이 뭐고 어떻게 챙기나"에 맞췄다.
- 2026 세부 수치는 단정하지 않고, 2025 공식 공개 예시는 참고 사례로만 넣었다.
- 본문은 체크리스트 중심으로 구성해 매년 세부 쿠폰과 기간이 달라져도 재사용 가능하게 맞췄다.

## Current Task

- [ ] `KT엠모바일` 주제로 Trend Desk용 한국어 SEO 블로그 패키지 작성
- [ ] 공식 확인 포인트만 남기고 취약계층 전용 요금제의 구체 혜택은 추정하지 않기
- [ ] `body_html`을 허용 태그만 사용해 1300~1800자 수준으로 구성하기
- [ ] 마지막에 `../categories/digital-services.html`과 `../archive.html` 링크를 포함하기

## Current Review

- 진행 중
