import os
import re
import requests
import subprocess
import whisper

# === 0) 환경 변수 ===
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")

print("SUPABASE_URL:", SUPABASE_URL)
print("SUPABASE_API_KEY:", "***")

HEADERS = {
    "apikey": SUPABASE_API_KEY,
    "Authorization": f"Bearer {SUPABASE_API_KEY}"
}

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
row_id = row['id']
print(f"Processing row ID: {row_id}")

# === 2) 이미지, 오디오 다운로드 ===
image_url = row['image_url']
audio_url = row['audio_url']

print("Image URL:", image_url)
print("Audio URL:", audio_url)

with open("background.png", "wb") as f:
    f.write(requests.get(image_url).content)

with open("audio.mp3", "wb") as f:
    f.write(requests.get(audio_url).content)

# === 3) Whisper로 STT → SRT 자막 생성 ===
model = whisper.load_model("small")  # or "base", "medium", "large" 등
result = model.transcribe("audio.mp3", language="ko")  # 한국어면 "ko"

# === Whisper 자막 SRT 저장 ===
def segments_to_srt(segments, path):
    def format_timestamp(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"

    with open(path, "w", encoding="utf-8") as f:
        for i, segment in enumerate(segments, start=1):
            start = format_timestamp(segment["start"])
            end = format_timestamp(segment["end"])
            text = segment["text"].strip()
            f.write(f"{i}\n{start} --> {end}\n{text}\n\n")

segments_to_srt(result["segments"], "subtitle.srt")
print("✅ Whisper SRT 생성 완료!")

# === 4) Supabase Storage에 SRT 업로드 ===
with open("subtitle.srt", "rb") as f:
    srt_upload = requests.post(
        f"{SUPABASE_URL}/storage/v1/object/newsletter-video-srt/subtitle_{row_id}.srt",
        headers={
            "Authorization": f"Bearer {SUPABASE_API_KEY}",
            "Content-Type": "application/x-subrip"
        },
        data=f
    )

print("SRT Upload response:", srt_upload.status_code, srt_upload.text)

# === 5) DB에 subtitle_url 업데이트 ===
subtitle_url = f"{SUPABASE_URL}/storage/v1/object/public/newsletter-video-srt/subtitle_{row_id}.srt"

patch_subtitle = requests.patch(
    f"{SUPABASE_URL}/rest/v1/newsletter?id=eq.{row_id}",
    headers={
        "apikey": SUPABASE_API_KEY,
        "Authorization": f"Bearer {SUPABASE_API_KEY}",
        "Content-Type": "application/json"
    },
    json={"subtitle_url": subtitle_url}
)
print("PATCH subtitle_url response:", patch_subtitle.status_code, patch_subtitle.text)

# === 6) FFmpeg로 이미지+오디오+자막 합치기 ===
subprocess.run([
    "ffmpeg",
    "-loop", "1",
    "-i", "background.png",
    "-i", "audio.mp3",
    "-vf", "subtitles=subtitle.srt:force_style='FontName=Noto Sans CJK SC,FontSize=24,OutlineColour=&H80000000,BorderStyle=1,Outline=2'",
    "-shortest",
    "-pix_fmt", "yuv420p",
    "output.mp4"
], check=True)

print("✅ Final video with subtitle done.")

# === 7) Supabase Storage에 영상 업로드 ===
with open("output.mp4", "rb") as f:
    upload = requests.post(
        f"{SUPABASE_URL}/storage/v1/object/newsletter-video/video_{row_id}.mp4",
        headers={
            "Authorization": f"Bearer {SUPABASE_API_KEY}",
            "Content-Type": "application/octet-stream"
        },
        data=f
    )

print("Video Upload response:", upload.status_code, upload.text)

# === 8) video_url 컬럼 PATCH ===
public_url = f"{SUPABASE_URL}/storage/v1/object/public/newsletter-video/video_{row_id}.mp4"

patch = requests.patch(
    f"{SUPABASE_URL}/rest/v1/newsletter?id=eq.{row_id}",
    headers={
        "apikey": SUPABASE_API_KEY,
        "Authorization": f"Bearer {SUPABASE_API_KEY}",
        "Content-Type": "application/json"
    },
    json={"video_url": public_url}
)

print("PATCH video_url response:", patch.status_code, patch.text)
print("✅ 동영상 생성 및 업로드 완료!")