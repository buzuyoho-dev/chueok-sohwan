"""인스타에 올라간 게시물(published/날짜/)을 구글 블로그와 스레드에 이어서 올린다.

순서: 블로그 먼저(글 주소를 얻음) → 스레드(본문에 블로그 링크).
각 플랫폼은 시크릿이 없으면 조용히 건너뛴다. 이미 올린 곳은 기록 파일로 판단해 다시 올리지 않는다.
  published/날짜/BLOG_URL, published/날짜/THREADS_ID

환경변수
  공통: GITHUB_REPOSITORY, (선택) BRANCH=main, POST_DATE, DRY_RUN=1, ONLY=blog|threads
  블로그: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN, BLOG_ID
  스레드: THREADS_TOKEN

블로그 본문: 날짜 폴더에 blog.md 가 있으면 그것을 쓰고, 없으면 캡션으로 기본 글을 만든다.
blog.md 규칙: 첫 줄 '# 제목'(선택), '## 소제목', 빈 줄로 문단 구분, '[[3]]' 은 3번 카드 이미지 자리.
"""
import os, re, json, time, glob, html, datetime, urllib.request, urllib.parse, urllib.error

KST = datetime.timezone(datetime.timedelta(hours=9))
DRY = bool(os.environ.get("DRY_RUN"))
ONLY = os.environ.get("ONLY", "").strip()
DISCLOSURE = ""  # 제휴 링크를 넣기 시작하면 고지 문구를 여기에 넣는다(공정위 지침).


def http(method, url, data=None, headers=None, secret=""):
    body = None
    headers = dict(headers or {})
    if data is not None:
        if headers.get("Content-Type") == "application/json":
            body = json.dumps(data, ensure_ascii=False).encode()
        else:
            body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        msg = e.read().decode(errors="replace")
        if secret:
            msg = msg.replace(secret, "***")
        raise RuntimeError(f"API 오류 {e.code} {url.split('?')[0]}: {msg}")


def load_post(folder):
    imgs = sorted(glob.glob(f"{folder}/*.jpg"), key=lambda p: int(os.path.basename(p).split(".")[0]))
    caption = open(f"{folder}/caption.txt", encoding="utf-8").read().strip()
    repo = os.environ.get("GITHUB_REPOSITORY", "buzuyoho-dev/chueok-sohwan")
    branch = os.environ.get("BRANCH", "main")
    urls = [f"https://raw.githubusercontent.com/{repo}/{branch}/{urllib.parse.quote(p)}" for p in imgs]
    return urls, caption


def split_caption(caption):
    """캡션을 (본문 줄들, 해시태그 목록)으로 나눈다."""
    lines = caption.splitlines()
    tags = []
    body = []
    for ln in lines:
        if ln.strip().startswith("#") and all(w.startswith("#") for w in ln.split()):
            tags += [w[1:] for w in ln.split()]
        else:
            body.append(ln)
    while body and not body[-1].strip():
        body.pop()
    return body, tags


EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿️]")


def clean_title(s):
    return EMOJI.sub("", s).strip()


# ---------------- 블로그 ----------------

def img_tag(url, n, alt):
    return (f'<div style="text-align:center;margin:16px 0"><img src="{url}" alt="{html.escape(alt)} {n}" '
            f'style="max-width:100%;width:540px;border-radius:6px" loading="lazy"></div>')


def blog_html(folder, urls, caption):
    body, tags = split_caption(caption)
    title = clean_title(body[0]) if body else "추억소환소"
    md_path = f"{folder}/blog.md"
    parts = []
    used = set()
    if os.path.exists(md_path):
        md = open(md_path, encoding="utf-8").read().strip()
        blocks = re.split(r"\n\s*\n", md)
        if blocks and blocks[0].startswith("# "):
            title = blocks.pop(0)[2:].strip()
        for b in blocks:
            b = b.strip()
            m = re.fullmatch(r"\[\[(\d+)\]\]", b)
            if m:
                n = int(m.group(1))
                if 1 <= n <= len(urls):
                    parts.append(img_tag(urls[n - 1], n, title)); used.add(n)
            elif b.startswith("## "):
                parts.append(f"<h2>{html.escape(b[3:].strip())}</h2>")
            else:
                parts.append("<p>" + "<br>".join(html.escape(x) for x in b.splitlines()) + "</p>")
    else:
        intro = [x for x in body[1:] if x.strip() and not x.startswith(("기준:", "출처:"))]
        parts.append("<p>" + "<br>".join(html.escape(x) for x in intro) + "</p>")
        for i, u in enumerate(urls, 1):
            parts.append(img_tag(u, i, title)); used.add(i)
    meta = [x for x in body if x.startswith(("기준:", "출처:"))]
    if meta:
        parts.append('<p style="color:#777;font-size:0.9em">' + "<br>".join(html.escape(x) for x in meta) + "</p>")
    parts.append('<p>더 많은 추억 카드는 인스타그램 '
                 '<a href="https://www.instagram.com/chueok.sohwan/">@chueok.sohwan</a>에서 매일 저녁 8시 30분에 올라와요.</p>')
    if DISCLOSURE:
        parts.append(f'<p style="color:#777;font-size:0.85em">{html.escape(DISCLOSURE)}</p>')
    labels = [t for t in tags if t != "추억소환소"][:8]
    return title, "\n".join(parts), labels


def google_token():
    r = http("POST", "https://oauth2.googleapis.com/token", {
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }, secret=os.environ["GOOGLE_REFRESH_TOKEN"])
    return r["access_token"]


def post_blog(folder, urls, caption):
    need = ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN", "BLOG_ID"]
    if any(not os.environ.get(k) for k in need):
        print("블로그: 시크릿 없음, 건너뜀"); return None
    rec = f"{folder}/BLOG_URL"
    if os.path.exists(rec):
        url = open(rec).read().strip(); print("블로그: 이미 게시됨", url); return url
    title, content, labels = blog_html(folder, urls, caption)
    tok = google_token()
    blog_id = os.environ["BLOG_ID"].strip()
    if DRY:
        info = http("GET", f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}",
                    headers={"Authorization": f"Bearer {tok}"}, secret=tok)
        print("블로그 연결 OK:", info.get("name"), info.get("url"))
        print("블로그 시험 출력:", title, labels, f"본문 {len(content)}자")
        return info.get("url")
    r = http("POST", f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts/",
             {"kind": "blogger#post", "title": title, "content": content, "labels": labels},
             headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}, secret=tok)
    url = r.get("url", "")
    open(rec, "w").write(url)
    print("블로그: 게시 완료", url)
    return url


# ---------------- 스레드 ----------------

TH_API = "https://graph.threads.net/v1.0"


def th(method, path, **params):
    tok = os.environ["THREADS_TOKEN"].strip()
    params["access_token"] = tok
    q = urllib.parse.urlencode(params)
    if method == "GET":
        return http("GET", f"{TH_API}/{path}?{q}", secret=tok)
    return http("POST", f"{TH_API}/{path}", params, secret=tok)


def th_wait(cid):
    for _ in range(36):
        st = th("GET", cid, fields="status,error_message")
        if st.get("status") == "FINISHED":
            return
        if st.get("status") in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"스레드 컨테이너 {cid} 상태 {st}")
        time.sleep(5)
    raise RuntimeError(f"스레드 컨테이너 {cid} 준비 시간 초과")


def threads_text(caption, blog_url):
    body, tags = split_caption(caption)
    lines = [x for x in body if not x.startswith(("기준:", "출처:"))]
    text = "\n".join(lines).strip()
    src = [x for x in body if x.startswith("출처:")]
    if src:
        text += "\n\n" + src[0]
    if blog_url:
        text += f"\n\n전체 이야기 👉 {blog_url}"
    if len(text) > 500:  # 스레드 글자 수 한도
        text = text[:497] + "…"
    return text


def post_threads(folder, urls, caption, blog_url):
    if not os.environ.get("THREADS_TOKEN"):
        print("스레드: 시크릿 없음, 건너뜀"); return
    rec = f"{folder}/THREADS_ID"
    if os.path.exists(rec):
        print("스레드: 이미 게시됨"); return
    text = threads_text(caption, blog_url)
    if DRY:
        me = th("GET", "me", fields="username")
        print("스레드 연결 OK: @" + me.get("username", "?"))
        print("스레드 시험 출력:\n" + text); return
    if len(urls) == 1:
        cid = th("POST", "me/threads", media_type="IMAGE", image_url=urls[0], text=text)["id"]
    else:
        kids = []
        for u in urls[:20]:
            k = th("POST", "me/threads", media_type="IMAGE", image_url=u, is_carousel_item="true")["id"]
            kids.append(k)
        for k in kids:
            th_wait(k)
        cid = th("POST", "me/threads", media_type="CAROUSEL", children=",".join(kids), text=text)["id"]
    th_wait(cid)
    mid = th("POST", "me/threads_publish", creation_id=cid)["id"]
    open(rec, "w").write(mid)
    print("스레드: 게시 완료", mid)


def main():
    day = os.environ.get("POST_DATE") or datetime.datetime.now(KST).strftime("%Y-%m-%d")
    folder = f"published/{day}"
    if not os.path.isdir(folder):
        print(f"{day}: 인스타 게시 기록이 없어 이어 올리지 않음"); return
    urls, caption = load_post(folder)
    errors = []
    blog_url = None
    if ONLY in ("", "blog"):
        try:
            blog_url = post_blog(folder, urls, caption)
        except Exception as e:
            errors.append(f"블로그 실패: {e}")
    elif os.path.exists(f"{folder}/BLOG_URL"):
        blog_url = open(f"{folder}/BLOG_URL").read().strip()
    if ONLY in ("", "threads"):
        try:
            post_threads(folder, urls, caption, blog_url)
        except Exception as e:
            errors.append(f"스레드 실패: {e}")
    if errors:
        raise SystemExit("\n".join(errors))


if __name__ == "__main__":
    main()
