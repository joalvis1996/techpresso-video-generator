import os
import requests

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")

headers = {
    "apikey": SUPABASE_API_KEY,
    "Authorization": f"Bearer {SUPABASE_API_KEY}"
}

# === 1단계: 영상화된 subject 목록 가져오기 ===
video_subjects_url = f"{SUPABASE_URL}/rest/v1/newsletter_videos?select=included_newsletter_ids,subject"
res = requests.get(video_subjects_url, headers=headers)
video_subjects_data = res.json()

used_subjects = set()
for item in video_subjects_data:
    if item.get("subject"):
        used_subjects.add(item["subject"])

print("✅ 영상화된 subject 수:", len(used_subjects))

# === 2단계: 모든 뉴스 가져온 후 필터링 ===
all_news_url = f"{SUPABASE_URL}/rest/v1/newsletter?select=id,subject,news_style_content&order=id.asc"
news_res = requests.get(all_news_url, headers=headers)
all_news = news_res.json()

# 필터링: 아직 영상화되지 않은 subject만 추출
new_subjects = {}
for item in all_news:
    subj = item.get("subject")
    if subj and subj not in used_subjects:
        new_subjects.setdefault(subj, []).append(item)

print("✅ 영상화 대상 subject 수:", len(new_subjects))