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

# === 1) youtube_url이 있는 모든 row 가져오기 ===
url = (
    f"{SUPABASE_URL}/rest/v1/newsletter"
    "?youtube_url=not.is.null"
    "&select=*"
)
res = requests.get(url, headers=HEADERS)
videos = res.json()
print(f"조회수 갱신 대상 rows ({len(videos)}):", [v["id"] for v in videos])

if not videos:
    print("✅ 업데이트할 영상 없음.")
    exit()

# === 2) OAuth token.json 가져오기 ===
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

# === 3) 유튜브 인증 ===
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

# === 4) 모든 row 반복해서 조회수 가져오고 DB 업데이트 ===
for row in videos:
    row_id = row['id']
    youtube_url = row['youtube_url']
    video_id = youtube_url.split("/")[-1]

    response = youtube.videos().list(
        part="statistics",
        id=video_id
    ).execute()

    items = response.get('items', [])
    if not items:
        print(f"❌ Video ID '{video_id}' 조회 실패. row_id: {row_id}")
        continue

    view_count = items[0]['statistics'].get('viewCount')
    print(f"✅ Video ID {video_id} 현재 조회수: {view_count}")

    if view_count is not None:
        patch = requests.patch(
            f"{SUPABASE_URL}/rest/v1/newsletter?id=eq.{row_id}",
            headers={
                "apikey": SUPABASE_API_KEY,
                "Authorization": f"Bearer {SUPABASE_API_KEY}",
                "Content-Type": "application/json"
            },
            json={"youtube_views": int(view_count)}
        )
        print(f"PATCH row_id={row_id} response:", patch.status_code, patch.text)
    else:
        print(f"❗️ Video ID {video_id} view_count=None → DB 업데이트 생략")

print("✅ 모든 row 조회수 갱신 완료")