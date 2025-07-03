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

# === 1) 업로드할 영상 가져오기 ===
url = (
    f"{SUPABASE_URL}/rest/v1/newsletter"
    "?video_url=not.is.null"   # video_url이 null이 아닌 row
    "&youtube_url=is.null"     # youtube_url이 null인 row
    "&select=*"
)
res = requests.get(url, headers=HEADERS)
videos = res.json()
print("Supabase 영상 rows:", videos)

if not videos:
    print("✅ 업로드할 영상 없음.")
    exit()

row = videos[0]
row_id = row['id']
video_url = row['video_url']
title = row['title']
description = row['content']

print(f"Processing row ID: {row_id}")
print(f"Video URL: {video_url}")

# === 2) 영상 다운로드 ===
video_file = f"upload_{row_id}.mp4"
with open(video_file, "wb") as f:
    f.write(requests.get(video_url).content)

print("✅ 영상 다운로드 완료")

# 1) 사인드 URL 요청
sign_res = requests.post(
    f"{SUPABASE_URL}/storage/v1/object/sign/youtube-oauth/token.json",
    headers=HEADERS,
    json={"expiresIn": 3600}
)
print("Signed URL response:", sign_res.status_code, sign_res.text)
sign_res.raise_for_status()

signed_url = sign_res.json()["signedURL"]

# 2) 절대 경로 만들기 (중복 X)
# 만약 signedURL이 "/object/sign/youtube-oauth/..." 형태라면
# 이미 경로가 포함되어 있으므로 SUPABASE_URL만 붙임
download_url = f"{SUPABASE_URL}/storage/v1{signed_url}"


# 3) 파일 가져오기
file_resp = requests.get(download_url)
print("Signed URL download status:", file_resp.status_code)

if file_resp.status_code == 200:
    with open("token.json", "wb") as f:
        f.write(file_resp.content)
    print("✅ OAuth 파일 다운로드 완료")
    print("token.json 내용:", file_resp.text)
else:
    print("❌ Signed URL 다운로드 실패:", file_resp.text)
    exit(1)

# === 4) 유튜브 인증 ===
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
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

# === 5) 유튜브 쇼츠 업로드 ===
body = {
    "snippet": {
        "title": title[:95],
        "description": description[:5000],
        "tags": ["뉴스", "AI", "Techpresso"],
        "categoryId": "27"  # News & Politics
    },
    "status": {
        "privacyStatus": "public"
    }
}

print("🚀 유튜브 업로드 시작")

request = youtube.videos().insert(
    part="snippet,status",
    body=body,
    media_body=video_file
)
response = request.execute()
youtube_url = f"https://youtu.be/{response['id']}"

print("✅ 유튜브 업로드 완료:", youtube_url)

# === 6) DB에 youtube_url 업데이트 ===
patch = requests.patch(
    f"{SUPABASE_URL}/rest/v1/newsletter?id=eq.{row_id}",
    headers={
        "apikey": SUPABASE_API_KEY,
        "Authorization": f"Bearer {SUPABASE_API_KEY}",
        "Content-Type": "application/json"
    },
    json={"youtube_url": youtube_url}
)

print("PATCH youtube_url response:", patch.status_code, patch.text)
print("✅ DB 업데이트 완료")