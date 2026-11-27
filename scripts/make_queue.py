"""카드 폴더(dayN_이름_순서.jpg)와 가이드의 본문을 날짜별 queue 폴더로 옮긴다.
사용: python3 scripts/make_queue.py <카드폴더> <첫날 YYYY-MM-DD> <본문 md> [--approve]"""
import sys, os, re, glob, shutil, datetime
src, start, md = sys.argv[1:4]; approve = "--approve" in sys.argv
d0 = datetime.date.fromisoformat(start)
text = open(md, encoding="utf-8").read()
BAN = re.compile(r"댓글\s*(로|을|에|남|달|적)|댓글 👇|👇|남겨\s*주세요|적어\s*주세요|달아\s*주세요|태그해|알려\s*주세요|공유해\s*주세요|좋아요\s*(눌러|부탁)")
# 대표 규칙(2026-11-27): 댓글·반응을 권유·유도하는 말 금지. "어떻게 생각하세요?" 같은 질문까지만 허용.
caps = {int(m.group(1)): m.group(2).strip() for m in re.finditer(r"^## (\d+)일차[^\n]*\n(.*?)(?=^## |\Z)", text, re.S | re.M)}
bad = {n: BAN.search(c).group(0) for n, c in caps.items() if BAN.search(c)}
if bad: raise SystemExit(f"댓글 유도 문구 발견(대표 규칙 위반): {bad}")
for f in glob.glob(f"{src}/day*_*.jpg"):
    m = re.match(r"day(\d+)_.*_(\d+)\.jpg", os.path.basename(f)); n, i = int(m.group(1)), int(m.group(2))
    day = (d0 + datetime.timedelta(days=n - 1)).isoformat(); out = f"queue/{day}"
    os.makedirs(out, exist_ok=True); shutil.copy(f, f"{out}/{i}.jpg")
    open(f"{out}/caption.txt", "w", encoding="utf-8").write(caps[n] + "\n")
    if approve: open(f"{out}/APPROVED", "w").write("approved\n")
print("완료:", sorted(os.listdir("queue")))
