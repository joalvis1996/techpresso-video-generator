import os
import re
import requests
import subprocess
from aeneas.executetask import ExecuteTask
from aeneas.task import Task
from datetime import datetime, timedelta  # ✅ 추가

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

# === 3) 원문 텍스트 문장별로 줄바꿈 저장 ===
text_cleaned = re.sub(r'([.!?])\s*', r'\1\n', text).strip()

with open("transcript.txt", "w", encoding="utf-8") as f:
    f.write(text_cleaned)

print("✅ 문장 단위 줄바꿈 완료")
print("=== transcript.txt ===")
print(text_cleaned)
print("=======================")

# === 4) Forced Aligner로 SRT 생성 ===
config_string = (
    "task_language=eng"
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

# ✅ SRT 시간 전체 오프셋 보정 함수 추가
def shift_srt(filename, offset_seconds):
    fmt = "%H:%M:%S,%f"
    with open(filename, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        if "-->" in line:
            start, end = line.strip().split(" --> ")
            start_dt = datetime.strptime(start, fmt)
            end_dt = datetime.strptime(end, fmt)
            delta = timedelta(seconds=offset_seconds)
            new_start = start_dt + delta
            new_end = end_dt + delta

            # 0 이하 방지
            zero_dt = datetime.strptime("00:00:00,000", fmt)
            if new_start < zero_dt:
                new_start = zero_dt
            if new_end < zero_dt:
                new_end = zero_dt

            new_line = "{} --> {}\n".format(
                new_start.strftime(fmt)[:-3],
                new_end.strftime(fmt)[:-3]
            )
            new_lines.append(new_line)
        else:
            new_lines.append(line)

    with open(filename, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

from datetime import datetime, timedelta

def shift_and_stretch_srt(filename, shift_seconds=-2, stretch_rate=0.98):
    """
    SRT 파일의 시간값을 shift + stretch 조합으로 보정
    - shift_seconds: 시작/종료 시간 모두 이동
    - stretch_rate: 전체 길이를 비율로 압축 (1.0 = 그대로)
    """
    fmt = "%H:%M:%S,%f"
    with open(filename, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        if "-->" in line:
            start, end = line.strip().split(" --> ")
            start_dt = datetime.strptime(start, fmt)
            end_dt = datetime.strptime(end, fmt)
            zero_dt = datetime.strptime("00:00:00,000", fmt)

            # 1) stretch 적용
            new_start = zero_dt + (start_dt - zero_dt) * stretch_rate
            new_end = zero_dt + (end_dt - zero_dt) * stretch_rate

            # 2) shift 적용
            new_start += timedelta(seconds=shift_seconds)
            new_end += timedelta(seconds=shift_seconds)

            # 음수 방지
            if new_start < zero_dt:
                new_start = zero_dt
            if new_end < zero_dt:
                new_end = zero_dt + timedelta(milliseconds=500)

            # 다시 문자열로 포맷
            new_line = "{} --> {}\n".format(
                new_start.strftime(fmt)[:-3],
                new_end.strftime(fmt)[:-3]
            )
            new_lines.append(new_line)
        else:
            new_lines.append(line)

    with open(filename, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    print(f"✅ SRT shift({shift_seconds}s) + stretch({stretch_rate*100:.1f}%) 완료!")

# === 사용 예시 ===
shift_and_stretch_srt("subtitle.srt", shift_seconds=-4, stretch_rate=0.97)

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
    "-vf", "subtitles=subtitle.srt:force_style='FontName=Noto Sans CJK SC,FontSize=24,OutlineColour=&H80000000,BorderStyle=1,Outline=2'",
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
print("✅ 동영상 생성 및 업로드 완료!")