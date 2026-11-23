"""카드 폴더(dayN_이름_순서.jpg)와 가이드의 본문을 날짜별 queue 폴더로 옮긴다.
사용: python3 scripts/make_queue.py <카드폴더> <첫날 YYYY-MM-DD> <본문 md> [--approve]"""
import sys, os, re, glob, shutil, datetime
src, start, md = sys.argv[1:4]; approve = "--approve" in sys.argv
d0 = datetime.date.fromisoformat(start)
text = open(md, encoding="utf-8").read()
caps = {int(m.group(1)): m.group(2).strip() for m in re.finditer(r"^## (\d+)일차[^\n]*\n(.*?)(?=^## |\Z)", text, re.S | re.M)}
for f in glob.glob(f"{src}/day*_*.jpg"):
    m = re.match(r"day(\d+)_.*_(\d+)\.jpg", os.path.basename(f)); n, i = int(m.group(1)), int(m.group(2))
    day = (d0 + datetime.timedelta(days=n - 1)).isoformat(); out = f"queue/{day}"
    os.makedirs(out, exist_ok=True); shutil.copy(f, f"{out}/{i}.jpg")
    open(f"{out}/caption.txt", "w", encoding="utf-8").write(caps[n] + "\n")
    if approve: open(f"{out}/APPROVED", "w").write("approved\n")
print("완료:", sorted(os.listdir("queue")))
