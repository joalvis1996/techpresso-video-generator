import requests
import os
from datetime import datetime

# 환경변수
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# Supabase headers
HEADERS = {
    "apikey": SUPABASE_API_KEY,
    "Authorization": f"Bearer {SUPABASE_API_KEY}",
    "Content-Type": "application/json"
}

# 1) Supabase에서 youtube_url 있는 rows 가져오기
url = f"{SUPABASE_URL}/rest/v1/newsletter"
params = {
    "youtube_url": "not.is.null",
    "youtube_views": "is.null",
    "select": "*"
}
res = requests.get(url, headers=HEADERS, params=params)
videos = res.json()

for video in videos:
    row_id = video['id']
    youtube_url = video['youtube_url']

    # video_id 추출
    video_id = youtube_url.split("v=")[-1].split("&")[0] if "v=" in youtube_url else youtube_url.split("/")[-1]

    # 2) 유튜브 Data API 호출
    yt_url = f"https://www.googleapis.com/youtube/v3/videos?part=statistics&id={video_id}&key={YOUTUBE_API_KEY}"
    yt_res = requests.get(yt_url).json()
    view_count = int(yt_res["items"][0]["statistics"]["viewCount"])

    print(f"Row ID: {row_id} | Views: {view_count}")

    # 3) Supabase에 조회수 업데이트
    patch = requests.patch(
        f"{SUPABASE_URL}/rest/v1/newsletter?id=eq.{row_id}",
        headers=HEADERS,
        json={
            "youtube_views": view_count,
            "youtube_views_last_updated": datetime.now().isoformat()
        }
    )
    print(f"Updated row {row_id}: {patch.status_code}")

print("✅ 조회수 갱신 완료")
