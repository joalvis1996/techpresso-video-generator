import os
import requests
import subprocess

# === 환경 변수 ===
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")

print("SUPABASE_URL:", SUPABASE_URL)
print("SUPABASE_API_KEY:", "***")

HEADERS = {
    "apikey": SUPABASE_API_KEY,
    "Authorization": f"Bearer {SUPABASE_API_KEY}"
}

# ✅ FFmpeg 폰트 경로 (fc-list | grep CJK 로 확인한 값!)
FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"

# === 1) Supabase에서 아직 영상 없는 row 가져오기 ===
url = f"{SUPABASE_URL}/rest/v1/newsletter?video_url=is.null&select=*"
res = requests.get(url, headers=HEADERS)
print("Response status:", res.status_code)

rows = res.json()
print("Response JSON:", rows)

if not rows:
    print("✅ No new rows to process.")
    exit()

row = rows[0]
print(f"Processing row ID: {row['id']}")

# === 2) 이미지, 오디오 다운로드 ===
image_url = row['image_url']
audio_url = row['audio_url']
text = row['news_style_content']

print("Image URL:", image_url)
print("Audio URL:", audio_url)

with open("background.png", "wb") as f:
    f.write(requests.get(image_url).content)

with open("audio.mp3", "wb") as f:
    f.write(requests.get(audio_url).content)

# === 2-1) 자막 저장 ===
with open("caption.txt", "w", encoding="utf-8") as f:
    f.write(text)

# === 3) FFmpeg 실행 ===
subprocess.run([
    "ffmpeg",
    "-loop", "1",
    "-i", "background.png",
    "-i", "audio.mp3",
    "-vf",
    (
        f"drawtext="
        f"fontfile={FONT_PATH}:"
        f"textfile=caption.txt:"
        f"fontcolor=white:"
        f"fontsize=40:"
        f"x=(w-text_w)/2:"
        f"y=h-100:"
        f"borderw=2:bordercolor=black"
    ),
    "-shortest",
    "-pix_fmt", "yuv420p",
    "output.mp4"
], check=True)

print("✅ FFmpeg rendering done.")

# === 4) Supabase Storage에 업로드 ===
with open("output.mp4", "rb") as f:
    upload = requests.post(
        f"{SUPABASE_URL}/storage/v1/object/newsletter-video/video_{row['id']}.mp4",
        headers={
            "Authorization": f"Bearer {SUPABASE_API_KEY}",
            "Content-Type": "application/octet-stream"
        },
        data=f
    )

print("Upload response:", upload.status_code, upload.text)

# === 5) video_url 컬럼 PATCH ===
public_url = f"{SUPABASE_URL}/storage/v1/object/public/newsletter-video/video_{row['id']}.mp4"

patch = requests.patch(
    f"{SUPABASE_URL}/rest/v1/newsletter?id=eq.{row['id']}",
    headers={
        "apikey": SUPABASE_API_KEY,
        "Authorization": f"Bearer {SUPABASE_API_KEY}",
        "Content-Type": "application/json"
    },
    json={"video_url": public_url}
)

print("PATCH response:", patch.status_code, patch.text)
print("✅ Process completed.")