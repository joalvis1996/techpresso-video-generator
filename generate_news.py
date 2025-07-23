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

# === 3단계: 첫 번째 subject만 선택 ===
if not new_subjects:
    print("✅ 처리할 subject가 없습니다.")
    exit()

first_subject, news_list = next(iter(new_subjects.items()))
print("🎬 처리할 subject:", first_subject)


# # 이후 news_list를 가지고 스크립트 생성, TTS/비디오 생성, Supabase 저장 등 처리

# # 예시: subject 기록용 dummy API 호출
# requests.post(
#     f"{SUPABASE_URL}/rest/v1/newsletter_videos",
#     headers={
#         "apikey": SUPABASE_API_KEY,
#         "Authorization": f"Bearer {SUPABASE_API_KEY}",
#         "Content-Type": "application/json"
#     },
#     json={"subject": first_subject, "included_newsletter_ids": ",".join(str(n["id"]) for n in news_list)}
# )
# print("✅ 처리된 subject 저장 완료:", first_subject)
