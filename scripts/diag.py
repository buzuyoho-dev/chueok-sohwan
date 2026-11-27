"""계정·게시물 진단(읽기 전용). 결과: inbox/diag.json"""
import os, json, datetime, urllib.request, urllib.parse, urllib.error
TOKEN=os.environ["IG_TOKEN"].strip(); UID=os.environ["IG_USER_ID"].strip()
API="https://graph.instagram.com/v21.0" if TOKEN.startswith("IG") else "https://graph.facebook.com/v21.0"
def get(path, **p):
    p["access_token"]=TOKEN
    try:
        with urllib.request.urlopen(f"{API}/{path}?"+urllib.parse.urlencode(p), timeout=60) as r: return json.load(r)
    except urllib.error.HTTPError as e: return {"error": e.read().decode(errors="replace").replace(TOKEN,"***")}
out={"at": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(timespec="minutes")}
out["account"]=get(UID, fields="username,name,followers_count,follows_count,media_count,biography,website,profile_picture_url")
out["account_insights_day"]=get(f"{UID}/insights", metric="reach,profile_views,accounts_engaged,views", period="day", metric_type="total_value")
media=get(f"{UID}/media", fields="id,caption,permalink,timestamp,media_type,media_product_type,like_count,comments_count,is_shared_to_feed", limit=20)
out["media"]=[]
for m in media.get("data",[]):
    m["caption"]=(m.get("caption") or "").split("\n")[0]
    m["insights"]=get(f"{m['id']}/insights", metric="reach,views,saved,shares,total_interactions,likes,comments")
    out["media"].append(m)
if "error" in media: out["media_error"]=media["error"]
os.makedirs("inbox",exist_ok=True); json.dump(out,open("inbox/diag.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
print(json.dumps(out,ensure_ascii=False,indent=1)[:6000])
