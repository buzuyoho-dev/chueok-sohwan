"""오늘(한국 시간) 날짜 폴더의 승인된 게시물을 인스타에 올린다.
폴더 구조: queue/YYYY-MM-DD/ 안에 1.jpg 2.jpg ... caption.txt, 그리고 승인 표시 APPROVED 파일.
환경변수: IG_TOKEN, IG_USER_ID, GITHUB_REPOSITORY, (선택) BRANCH=main, POST_DATE, DRY_RUN=1
DRY_RUN=1: 실제 게시 없이 ① 토큰·계정 확인 ② 이미지 주소 접속 확인 ③ 본문 출력만 한다.
토큰 종류 자동 판별: IG로 시작 = Instagram 로그인 토큰(graph.instagram.com),
그 외(EAA… 페이스북/시스템 사용자 토큰) = graph.facebook.com.
"""
import os, json, time, glob, shutil, urllib.request, urllib.parse, urllib.error, datetime

KST = datetime.timezone(datetime.timedelta(hours=9))
TOKEN = os.environ.get("IG_TOKEN", "").strip()
UID = os.environ.get("IG_USER_ID", "").strip()
API = "https://graph.instagram.com/v21.0" if TOKEN.startswith("IG") else "https://graph.facebook.com/v21.0"


def call(method, path, **params):
    params["access_token"] = TOKEN
    url = f"{API}/{path}"
    data = urllib.parse.urlencode(params)
    req = urllib.request.Request(url + "?" + data) if method == "GET" else \
        urllib.request.Request(url, data=data.encode(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace").replace(TOKEN, "***")
        raise SystemExit(f"API 오류 {e.code} {path}: {body}")


def wait_ready(cid):
    for _ in range(36):
        st = call("GET", cid, fields="status_code").get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            raise SystemExit(f"컨테이너 {cid} 상태 {st}")
        time.sleep(5)
    raise SystemExit(f"컨테이너 {cid} 준비 시간 초과")


def check_account():
    if not TOKEN or not UID:
        raise SystemExit("저장소 시크릿 IG_TOKEN 또는 IG_USER_ID가 비어 있음")
    print("토큰 종류:", "Instagram 로그인" if TOKEN.startswith("IG") else "페이스북/시스템 사용자", "→", API)
    me = call("GET", UID, fields="username")
    print("계정 확인 OK:", "@" + me.get("username", "?"), "(ID", UID + ")")
    try:
        lim = call("GET", f"{UID}/content_publishing_limit", fields="quota_usage,config")
        print("게시 한도 확인 OK:", json.dumps(lim.get("data", lim), ensure_ascii=False))
    except SystemExit as e:
        print("게시 한도 조회 실패(참고용):", e)


def check_urls(urls):
    bad = []
    for u in urls:
        try:
            with urllib.request.urlopen(urllib.request.Request(u, method="HEAD"), timeout=30) as r:
                if r.status != 200 or "image" not in r.headers.get("Content-Type", ""):
                    bad.append(u)
        except Exception:
            bad.append(u)
    if bad:
        raise SystemExit("이미지 주소 접속 실패: " + ", ".join(bad))
    print(f"이미지 {len(urls)}장 주소 접속 OK")


def main():
    dry = bool(os.environ.get("DRY_RUN"))
    day = os.environ.get("POST_DATE") or datetime.datetime.now(KST).strftime("%Y-%m-%d")
    folder = f"queue/{day}"
    if dry:
        check_account()
    if not os.path.isdir(folder):
        print(f"{day}: 올릴 게시물 없음"); return
    if not os.path.exists(f"{folder}/APPROVED"):
        print(f"{day}: 승인 안 됨, 건너뜀"); return
    imgs = sorted(glob.glob(f"{folder}/*.jpg"), key=lambda p: int(os.path.basename(p).split(".")[0]))
    caption = open(f"{folder}/caption.txt", encoding="utf-8").read().strip()
    if not 1 <= len(imgs) <= 10:
        raise SystemExit(f"이미지 수 {len(imgs)}개: 1~10개여야 함")
    repo = os.environ["GITHUB_REPOSITORY"]; branch = os.environ.get("BRANCH", "main")
    urls = [f"https://raw.githubusercontent.com/{repo}/{branch}/{urllib.parse.quote(p)}" for p in imgs]
    check_urls(urls)
    if dry:
        print(json.dumps({"day": day, "images": urls, "caption": caption}, ensure_ascii=False, indent=1))
        print("시험 실행 성공: 실제 게시는 하지 않았습니다."); return
    if len(urls) == 1:
        cid = call("POST", f"{UID}/media", image_url=urls[0], caption=caption)["id"]
    else:
        kids = []
        for u in urls:
            k = call("POST", f"{UID}/media", image_url=u, is_carousel_item="true")["id"]
            wait_ready(k); kids.append(k)
        cid = call("POST", f"{UID}/media", media_type="CAROUSEL", children=",".join(kids), caption=caption)["id"]
    wait_ready(cid)
    mid = call("POST", f"{UID}/media_publish", creation_id=cid)["id"]
    print(f"{day}: 게시 완료 media_id={mid}")
    os.makedirs("published", exist_ok=True)
    shutil.move(folder, f"published/{day}")
    open(f"published/{day}/MEDIA_ID", "w").write(mid)


if __name__ == "__main__":
    main()
