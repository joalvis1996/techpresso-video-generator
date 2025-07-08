import os
import requests
import json
import google.auth
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# === 0) Supabase 연결 ===
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")

HEADERS = {
    "apikey": SUPABASE_API_KEY,
    "Authorization": f"Bearer {SUPABASE_API_KEY}"
}

# === 1) youtube_url은 있으나 youtube_views가 null인 row만 가져오기 ===
url = (
    f"{SUPABASE_URL}/rest/v1/newsletter"
    "?youtube_url=not.is.null"
    "&youtube_views=is.null"
    "&select=*"
)
res = requests.get(url, headers=HEADERS)
videos = res.json()
print("Supabase 조회수 업데이트 대상 rows:", videos)

if not videos:
    print("✅ 업데이트할 영상 없음.")
    exit()

row = videos[0]
row_id = row['id']
youtube_url = row['youtube_url']

# === 2) OAuth token.json 가져오기 (upload_to_youtube.py와 동일) ===
sign_res = requests.post(
    f"{SUPABASE_URL}/storage/v1/object/sign/youtube-oauth/token.json",
    headers=HEADERS,
    json={"expiresIn": 3600}
)
print("Signed URL response:", sign_res.status_code, sign_res.text)
sign_res.raise_for_status()

signed_url = sign_res.json()["signedURL"]
download_url = f"{SUPABASE_URL}/storage/v1{signed_url}"

file_resp = requests.get(download_url)
print("Signed URL download status:", file_resp.status_code)

if file_resp.status_code == 200:
    with open("token.json", "wb") as f:
        f.write(file_resp.content)
    print("✅ OAuth 파일 다운로드 완료")
else:
    print("❌ Signed URL 다운로드 실패:", file_resp.text)
    exit(1)

# === 3) 유튜브 API 인증 ===
SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]
CLIENT_SECRETS_FILE = "client_secret.json"

creds = None
if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(google.auth.transport.requests.Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
        creds = flow.run_console()
    with open("token.json", "w") as token:
        token.write(creds.to_json())

youtube = build("youtube", "v3", credentials=creds)

# === 4) 조회수 가져오기 ===
video_id = youtube_url.split("/")[-1]

response = youtube.videos().list(
    part="statistics",
    id=video_id
).execute()

view_count = response['items'][0]['statistics']['viewCount']
print(f"✅ 현재 조회수: {view_count}")

# === 5) Supabase에 업데이트 ===
patch = requests.patch(
    f"{SUPABASE_URL}/rest/v1/newsletter?id=eq.{row_id}",
    headers={
        "apikey": SUPABASE_API_KEY,
        "Authorization": f"Bearer {SUPABASE_API_KEY}",
        "Content-Type": "application/json"
    },
    json={"youtube_views": int(view_count)}
)

print("PATCH youtube_views response:", patch.status_code, patch.text)
print("✅ DB youtube_views 업데이트 완료")
