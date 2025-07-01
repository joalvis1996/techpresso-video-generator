import os
import requests

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")
print(SUPABASE_URL)
print(SUPABASE_API_KEY)

HEADERS = {
    "apikey": SUPABASE_API_KEY,
    "Authorization": f"Bearer {SUPABASE_API_KEY}"
}

# 뉴스 row 가져오기 테스트
url = f"{SUPABASE_URL}/rest/v1/news?video_url=is.null&select=*"
res = requests.get(url, headers=HEADERS)
print("Response status:", res.status_code)
print("Response JSON:", res.json())


