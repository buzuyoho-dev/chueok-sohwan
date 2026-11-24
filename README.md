# 추억소환소 인스타 자동 게시

매일 20:30(한국 시간) GitHub Actions가 `queue/오늘날짜/`의 승인된 카드(1.jpg~, caption.txt, APPROVED)를 @chueok.sohwan에 캐러셀로 올리고 `published/`로 옮깁니다.

- 승인 표시(APPROVED)가 없는 날짜는 올라가지 않습니다.
- 예약 실행은 GitHub 사정으로 몇 분~수십 분 늦을 수 있습니다.
- 시험 실행: Actions → 매일 인스타 게시 → Run workflow → dry_run에 1 (실제 게시 없음, 토큰·계정·이미지 주소 확인)
- 토큰은 만료 없는 방식이라 주간 갱신 작업은 뺐습니다.

## 블로그·스레드 이어 올리기 (2026-11-24 추가)
인스타 게시가 끝나면 같은 작업에서 `scripts/crosspost.py`가 `published/오늘날짜/`를 구글 블로그(Blogger)와 스레드에 올립니다.
- 순서: 블로그 먼저 → 스레드 본문에 블로그 글 링크.
- 시크릿이 없는 플랫폼은 건너뜁니다. 이미 올린 곳은 `BLOG_URL`, `THREADS_ID` 기록 파일로 판단해 다시 올리지 않습니다.
- 블로그 본문: 날짜 폴더에 `blog.md`가 있으면 사용(`# 제목`, `## 소제목`, 빈 줄 문단, `[[3]]` = 3번 카드 자리). 없으면 캡션으로 기본 글.
- 필요한 시크릿: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`, `BLOG_ID`(블로그), `THREADS_TOKEN`(스레드).
- 지난 날짜 다시 올리기: Run workflow → post_date에 날짜, only에 `blog` 또는 `threads`. 시험은 dry_run에 1.
- 제휴 링크를 넣기 시작하면 `DISCLOSURE` 문구(수수료 고지)를 채운다.
