import os
import sys
import requests
import subprocess
import whisper

# === 0) 환경 변수 ===
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")

if not SUPABASE_URL or not SUPABASE_API_KEY:
    print("❌ 환경 변수 SUPABASE_URL 또는 SUPABASE_API_KEY가 설정되지 않았습니다.")
    sys.exit(1)

print("SUPABASE_URL:", SUPABASE_URL)
print("SUPABASE_API_KEY:", "***")

HEADERS = {
    "apikey": SUPABASE_API_KEY,
    "Authorization": f"Bearer {SUPABASE_API_KEY}"
}

# === 1) Supabase에서 아직 영상 없는 row 가져오기 ===
url = (
    f"{SUPABASE_URL}/rest/v1/newsletter"
    "?video_url=is.null"         # 아직 동영상 없음
    "&image_url=not.is.null"     # 이미지 있음
    "&audio_url=not.is.null"     # 오디오 있음
    "&select=*"
)
res = requests.get(url, headers=HEADERS)
print("Response status:", res.status_code)

if res.status_code != 200:
    print(f"❌ Supabase 요청 실패: {res.status_code} - {res.text}")
    sys.exit(1)

rows = res.json()
print("Response JSON:", rows)

if not rows:
    print("새로운 기사 없음.")
    sys.exit(0)

row = rows[0]
row_id = row['id']
print(f"Processing row ID: {row_id}")

# === 2) 이미지, 오디오 다운로드 ===
image_url = row.get('image_url')
audio_url = row.get('audio_url')

if not image_url or not audio_url:
    print(f"❌ 이미지 또는 오디오 URL이 없습니다. image_url: {image_url}, audio_url: {audio_url}")
    sys.exit(1)

print("Image URL:", image_url)
print("Audio URL:", audio_url)

try:
    img_res = requests.get(image_url, timeout=30)
    img_res.raise_for_status()
    with open("background.png", "wb") as f:
        f.write(img_res.content)
    print("✅ 이미지 다운로드 완료")
except requests.RequestException as e:
    print(f"❌ 이미지 다운로드 실패: {e}")
    sys.exit(1)

try:
    audio_res = requests.get(audio_url, timeout=30)
    audio_res.raise_for_status()
    with open("audio.mp3", "wb") as f:
        f.write(audio_res.content)
    print("✅ 오디오 다운로드 완료")
except requests.RequestException as e:
    print(f"❌ 오디오 다운로드 실패: {e}")
    sys.exit(1)

# === 3) Whisper로 STT → SRT 자막 생성 ===
try:
    print("Whisper 모델 로딩 중...")
    model = whisper.load_model("small")  # or "base", "medium", "large" 등
    print("✅ Whisper 모델 로딩 완료")
    print("음성 인식 중...")
    result = model.transcribe("audio.mp3", language="ko")  # 한국어면 "ko"
    print("✅ 음성 인식 완료")
except Exception as e:
    print(f"❌ Whisper 처리 실패: {e}")
    sys.exit(1)

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
print("Whisper SRT 생성 완료!")

# === 4) Supabase Storage에 SRT 업로드 ===
try:
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
    if srt_upload.status_code not in [200, 201]:
        print(f"❌ SRT 업로드 실패: {srt_upload.status_code} - {srt_upload.text}")
        sys.exit(1)
except Exception as e:
    print(f"❌ SRT 업로드 중 오류 발생: {e}")
    sys.exit(1)

# === 5) DB에 subtitle_url 업데이트 ===
subtitle_url = f"{SUPABASE_URL}/storage/v1/object/public/newsletter-video-srt/subtitle_{row_id}.srt"

try:
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
    if patch_subtitle.status_code not in [200, 204]:
        print(f"❌ subtitle_url 업데이트 실패: {patch_subtitle.status_code} - {patch_subtitle.text}")
        sys.exit(1)
except Exception as e:
    print(f"❌ subtitle_url 업데이트 중 오류 발생: {e}")
    sys.exit(1)

# === 6) FFmpeg로 이미지+오디오+자막 합치기 ===
try:
    print("FFmpeg로 비디오 생성 중...")
    subprocess.run([
        "ffmpeg",
        "-loop", "1",
        "-i", "background.png",
        "-i", "audio.mp3",
        "-vf", (
            "subtitles=subtitle.srt:"
            "force_style='FontName=Noto Sans CJK SC,FontSize=24,OutlineColour=&H80000000,BorderStyle=1,Outline=2',"
            "setpts=PTS/1.25"
        ),
        "-filter:a", "atempo=1.25",
        "-shortest",
        "-pix_fmt", "yuv420p",
        "-y",  # 덮어쓰기 허용
        "output.mp4"
    ], check=True, capture_output=True, text=True)
    print("✅ 비디오 생성 완료")
except subprocess.CalledProcessError as e:
    print(f"❌ FFmpeg 실행 실패: {e}")
    if e.stderr:
        print(f"에러 출력: {e.stderr}")
    sys.exit(1)
except FileNotFoundError:
    print("❌ FFmpeg가 설치되어 있지 않습니다. FFmpeg를 설치해주세요.")
    sys.exit(1)

# === 7) Supabase Storage에 영상 업로드 ===
try:
    if not os.path.exists("output.mp4"):
        print("❌ output.mp4 파일이 존재하지 않습니다.")
        sys.exit(1)
    
    with open("output.mp4", "rb") as f:
        upload = requests.post(
            f"{SUPABASE_URL}/storage/v1/object/newsletter-video/video_{row_id}.mp4",
            headers={
                "Authorization": f"Bearer {SUPABASE_API_KEY}",
                "Content-Type": "application/octet-stream"
            },
            data=f,
            timeout=300  # 큰 파일 업로드를 위한 타임아웃
        )
    
    print("Video Upload response:", upload.status_code, upload.text)
    if upload.status_code not in [200, 201]:
        print(f"❌ 비디오 업로드 실패: {upload.status_code} - {upload.text}")
        sys.exit(1)
except Exception as e:
    print(f"❌ 비디오 업로드 중 오류 발생: {e}")
    sys.exit(1)

# === 8) video_url 컬럼 PATCH ===
public_url = f"{SUPABASE_URL}/storage/v1/object/public/newsletter-video/video_{row_id}.mp4"

try:
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
    if patch.status_code not in [200, 204]:
        print(f"❌ video_url 업데이트 실패: {patch.status_code} - {patch.text}")
        sys.exit(1)
except Exception as e:
    print(f"❌ video_url 업데이트 중 오류 발생: {e}")
    sys.exit(1)

print("✅ 동영상 생성 및 업로드 완료!")

# === 9) 임시 파일 정리 (선택사항) ===
# 필요시 주석 해제하여 임시 파일 삭제
# for temp_file in ["background.png", "audio.mp3", "subtitle.srt", "output.mp4"]:
#     if os.path.exists(temp_file):
#         os.remove(temp_file)
#         print(f"임시 파일 삭제: {temp_file}")