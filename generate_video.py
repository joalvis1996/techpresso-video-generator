import os
import subprocess

# ✅ Secrets로 관리한 값 불러오기
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")
print("SUPABASE_URL:", SUPABASE_URL)
print("SUPABASE_API_KEY:", SUPABASE_API_KEY)

# ✅ 폰트 경로: fc-list 로 확인한 그대로
FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"

# ✅ drawtext 옵션: 한글 + 영문은 이 폰트로 OK
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
])
