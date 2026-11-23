"""댓글 관리. 토큰은 GitHub 시크릿에만 있고, Claude는 파일(inbox/outbox)로만 주고받는다.
MODE=fetch : 최근 게시물의 '아직 답 안 한' 댓글을 inbox/comments.json에 저장
MODE=reply : outbox/actions.json 실행 후 기록(state/handled.json)에 남기고 outbox 비움
  actions.json = [{"comment_id": "...", "do": "reply", "message": "..."},
                  {"comment_id": "...", "do": "hide"},      # 광고·스팸 숨김
                  {"comment_id": "...", "do": "skip"},      # 답 안 함(대표 보고용)
                  {"media_id": "...",   "do": "delete_post"}]  # 삭제 요청 시 게시물 내림
"""
import os, json, datetime, urllib.request, urllib.parse, urllib.error

TOKEN = os.environ.get("IG_TOKEN", "").strip(); UID = os.environ.get("IG_USER_ID", "").strip()
API = "https://graph.instagram.com/v21.0" if TOKEN.startswith("IG") else "https://graph.facebook.com/v21.0"
KST = datetime.timezone(datetime.timedelta(hours=9))


def call(method, path, **params):
    params["access_token"] = TOKEN
    q = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"{API}/{path}?{q}", method=method) if method in ("GET", "DELETE") else \
        urllib.request.Request(f"{API}/{path}", data=q.encode(), method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"error": e.read().decode(errors="replace").replace(TOKEN, "***")}


def load(p, default):
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else default


def save(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(obj, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def fetch():
    me = call("GET", UID, fields="username"); own = me.get("username")
    if not own:
        raise SystemExit(f"계정 조회 실패: {me}")
    handled = set(load("state/handled.json", {}).keys())
    media = call("GET", f"{UID}/media", fields="id,caption,permalink,timestamp,comments_count", limit=30)
    if "error" in media:
        raise SystemExit(f"게시물 조회 실패: {media['error']}")
    pending, errors = [], []
    for m in media.get("data", []):
        if not m.get("comments_count"):
            continue
        res = call("GET", f"{m['id']}/comments", fields="id,text,username,timestamp,replies{id,username,text}", limit=100)
        if "error" in res:
            errors.append(res["error"]); continue
        for c in res.get("data", []):
            if c.get("username") == own or c["id"] in handled:
                continue
            if any(r.get("username") == own for r in c.get("replies", {}).get("data", [])):
                continue
            pending.append({"comment_id": c["id"], "media_id": m["id"], "permalink": m.get("permalink"),
                            "post": (m.get("caption") or "").split("\n")[0], "username": c.get("username"),
                            "text": c.get("text"), "timestamp": c.get("timestamp")})
    save("inbox/comments.json", {"fetched_at": datetime.datetime.now(KST).isoformat(timespec="minutes"),
                                 "account": own, "pending": pending, "errors": errors})
    print(f"@{own}: 게시물 {len(media.get('data', []))}개, 답할 댓글 {len(pending)}개, 오류 {len(errors)}건")
    for e in errors:
        print("오류:", e)


def reply():
    acts = load("outbox/actions.json", [])
    handled = load("state/handled.json", {}); now = datetime.datetime.now(KST).isoformat(timespec="minutes")
    fails = 0
    for a in acts:
        do = a.get("do"); key = a.get("comment_id") or a.get("media_id")
        if do == "reply":
            r = call("POST", f"{a['comment_id']}/replies", message=a["message"])
        elif do == "hide":
            r = call("POST", a["comment_id"], hide="true")
        elif do == "delete_post":
            r = call("DELETE", a["media_id"])
        else:
            r = {"ok": "skip"}
        ok = "error" not in r; fails += not ok
        print(("OK  " if ok else "실패"), do, key, "" if ok else r["error"])
        if ok:
            handled[key] = {"do": do, "at": now, "message": a.get("message")}
    save("state/handled.json", handled)
    if os.path.exists("outbox/actions.json"):
        os.remove("outbox/actions.json")
    if fails:
        raise SystemExit(f"{fails}건 실패")


if __name__ == "__main__":
    {"fetch": fetch, "reply": reply}[os.environ.get("MODE", "fetch")]()
