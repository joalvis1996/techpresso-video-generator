import os
import requests
import subprocess
from aeneas.executetask import ExecuteTask
from aeneas.task import Task

# === 0) 환경 변수 ===
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")

print("SUPABASE_URL:", SUPABASE_URL)
print("SUPABASE_API_KEY:", "***")

HEADERS = {
    "apikey": SUPABASE_API_KEY,
    "Authorization": f"Bearer {SUPABASE_API_KEY}"
}

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
row_id = row['id']
print(f"Processing row ID: {row_id}")

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

# === 3) 원문 텍스트 저장 ===
with open("transcript.txt", "w", encoding="utf-8") as f:
    f.write(text)

# === 4) aeneas Forced Aligner로 SRT 생성 ===
# ✅ config_string 수정!
config_string = (
    "task_language=kor"
    "|is_text_type=plain"
    "|os_task_file_format=srt"
    "|is_audio_file_already_synthesized=yes"
)
task = Task(config_string=config_string)
task.audio_file_path_absolute = os.path.abspath("audio.mp3")
task.text_file_path_absolute = os.path.abspath("transcript.txt")
task.sync_map_file_path_absolute = os.path.abspath("subtitle.srt")

ExecuteTask(task).execute()
task.output_sync_map_file()
print("✅ aeneas SRT 생성 완료!")

# === 5) Supabase Storage에 SRT 업로드 ===
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

# === 6) DB에 subtitle_url 업데이트 ===
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

# === 7) FFmpeg로 이미지+오디오+자막 합치기 ===
subprocess.run([
    "ffmpeg",
    "-loop", "1",
    "-i", "background.png",
    "-i", "audio.mp3",
    "-vf", f"subtitles=subtitle.srt:force_style='FontName=Noto Sans CJK SC,FontSize=40,OutlineColour=&H80000000,BorderStyle=1,Outline=2'",
    "-shortest",
    "-pix_fmt", "yuv420p",
    "output.mp4"
], check=True)

print("✅ Final video with subtitle done.")

# === 8) Supabase Storage에 영상 업로드 ===
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

# === 9) video_url 컬럼 PATCH ===
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
print("동영상 생성 완료!")