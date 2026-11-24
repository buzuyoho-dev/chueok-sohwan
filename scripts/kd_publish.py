#!/usr/bin/env python3
"""Korea Decoded 자동 게시: 오늘(KST) 날짜 폴더의 글을 품질 검사 후 Blogger에 올린다.

폴더 구조: korea-decoded/queue/YYYY-MM-DD/post.json
  {"term": "jeonse", "title": "...", "labels": [...], "html": "..."}
품질 검사를 통과하지 못하면 게시하지 않고 실패로 끝난다(Actions 실패 알림).
"""
import datetime, html, json, os, re, shutil, sys, urllib.parse, urllib.request

ROOT = os.path.join(os.path.dirname(__file__), "..", "korea-decoded")
QUEUE, DONE = os.path.join(ROOT, "queue"), os.path.join(ROOT, "published")
TERMS = os.path.join(ROOT, "terms.json")
BLOG_ID = os.environ.get("KD_BLOG_ID", "6591486499474318581")
REQUIRED = ["In one line", "Where the word comes from", "In the news", "Don't confuse it with", "Sources"]
MIN_CHARS = 1500


def check(post, used):
    errs = []
    body = post["html"]
    heads = [html.unescape(h).strip() for h in re.findall(r"<h2[^>]*>(.*?)</h2>", body, re.S)]
    for r in REQUIRED:
        if r not in heads:
            errs.append(f"missing section: {r}")
    src = body.split(">Sources</h2>", 1)[-1] if ">Sources</h2>" in body else ""
    links = set(re.findall(r'href="(https?://[^"]+)"', src))
    domains = {urllib.parse.urlparse(u).netloc.replace("www.", "") for u in links}
    if len(domains) < 2:
        errs.append(f"need sources from 2+ sites, got {len(domains)}")
    text = re.sub(r"<[^>]+>", " ", body)
    if len(re.sub(r"\s+", " ", text)) < MIN_CHARS:
        errs.append("too short")
    figs = re.findall(r"<figure[^>]*>(.*?)</figure>", body, re.S)
    if not 1 <= len(figs) <= 2:
        errs.append(f"need 1-2 images, got {len(figs)}")
    for f in figs:
        if not re.search(r'<img [^>]*src="https://upload\.wikimedia\.org/', f) or ' alt="' not in f:
            errs.append("image must be a Wikimedia Commons file with alt text")
        if not re.search(r"<figcaption>.*Wikimedia Commons.*</figcaption>", f, re.S):
            errs.append("image needs a credit caption (author, license, Wikimedia Commons)")
    if len(re.findall(r"<img ", body)) != len(figs):
        errs.append("every image must sit in a <figure> with credit")
    if post["term"].lower() in used:
        errs.append(f"duplicate term: {post['term']}")
    return errs


def token():
    data = urllib.parse.urlencode({
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
        "grant_type": "refresh_token"}).encode()
    with urllib.request.urlopen("https://oauth2.googleapis.com/token", data) as r:
        return json.load(r)["access_token"]


def api(method, path, tok, body=None):
    req = urllib.request.Request(
        f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}{path}", method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def ensure_pages(tok):
    """korea-decoded/pages/*.json 중 블로그에 없는 페이지를 만든다."""
    existing = {p["title"] for p in api("GET", "/pages", tok).get("items", [])}
    for f in sorted(os.listdir(os.path.join(ROOT, "pages"))):
        p = json.load(open(os.path.join(ROOT, "pages", f), encoding="utf-8"))
        if p["title"] not in existing:
            r = api("POST", "/pages", tok, {"title": p["title"], "content": p["html"]})
            print("page created:", r.get("url"))


def main():
    dry = "--dry-run" in sys.argv
    today = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)).strftime("%Y-%m-%d")
    day = next((a for a in sys.argv[1:] if re.match(r"\d{4}-\d{2}-\d{2}$", a)), today)
    used = set(json.load(open(TERMS))) if os.path.exists(TERMS) else set()
    # 대기열 전체 검사(오늘 것뿐 아니라 미리 문제를 잡기 위해)
    bad = False
    for d in sorted(os.listdir(QUEUE)):
        pj = os.path.join(QUEUE, d, "post.json")
        if os.path.exists(pj):
            errs = check(json.load(open(pj, encoding="utf-8")), used)
            print(d, "OK" if not errs else errs)
            bad |= bool(errs) and d == day
    if dry:
        return
    tok = token()
    ensure_pages(tok)
    pj = os.path.join(QUEUE, day, "post.json")
    if not os.path.exists(pj):
        print("no post for", day); return
    if bad:
        sys.exit("quality check failed; not publishing")
    post = json.load(open(pj, encoding="utf-8"))
    r = api("POST", "/posts/", tok, {"title": post["title"], "content": post["html"], "labels": post.get("labels", [])})
    print("published:", r.get("url"))
    used.add(post["term"].lower())
    json.dump(sorted(used), open(TERMS, "w"), indent=1)
    post["url"] = r.get("url")
    json.dump(post, open(pj, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    shutil.move(os.path.join(QUEUE, day), os.path.join(DONE, day))


if __name__ == "__main__":
    main()
