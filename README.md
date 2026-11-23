# 추억소환소 인스타 자동 게시

매일 20:30(한국 시간) GitHub Actions가 `queue/오늘날짜/`의 승인된 카드(1.jpg~, caption.txt, APPROVED)를 @chueok.sohwan에 캐러셀로 올리고 `published/`로 옮깁니다.

- 승인 표시(APPROVED)가 없는 날짜는 올라가지 않습니다.
- 예약 실행은 GitHub 사정으로 몇 분~수십 분 늦을 수 있습니다.
- 시험 실행: Actions → 매일 인스타 게시 → Run workflow → dry_run에 1 (실제 게시 없음, 토큰·계정·이미지 주소 확인)
- 토큰은 만료 없는 방식이라 주간 갱신 작업은 뺐습니다.
