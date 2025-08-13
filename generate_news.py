import os
import requests

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")

headers = {
    "apikey": SUPABASE_API_KEY,
    "Authorization": f"Bearer {SUPABASE_API_KEY}"
}

video_subjects_url = f"{SUPABASE_URL}/rest/v1/newsletter_videos?select=included_newsletter_ids,subject"
res = requests.get(video_subjects_url, headers=headers)
video_subjects_data = res.json()

used_subjects = set()
for item in video_subjects_data:
    if item.get("subject"):
        used_subjects.add(item["subject"])

# 모든 뉴스 가져온 후 필터링 ===
all_news_url = f"{SUPABASE_URL}/rest/v1/newsletter?select=id,subject,news_style_content&order=id.asc"
news_res = requests.get(all_news_url, headers=headers)
all_news = news_res.json()

# 아직 영상화되지 않은 subject만 추출
new_subjects = {}
for item in all_news:
    subj = item.get("subject")
    if subj and subj not in used_subjects:
        new_subjects.setdefault(subj, []).append(item)

# 첫 번째 subject만 선택
if not new_subjects:
    exit()

first_subject, news_list = next(iter(new_subjects.items()))

# 뉴스 스크립트 구성
script_lines = []
script_lines.append("오늘의 뉴스를 전해드립니다.\n")

for idx, news in enumerate(news_list, 1):
    content = news.get("news_style_content")
    if content:
        script_lines.append(f"[{idx}] {content.strip()}")
        if idx < len(news_list):
            script_lines.append("다음 뉴스입니다.\n")

script_lines.append("\n이상으로 오늘의 주요 뉴스를 전해드렸습니다. 감사합니다.")

# 스크립트 파일로 저장
output_script_path = "compiled_script.txt"
with open(output_script_path, "w", encoding="utf-8") as f:
    f.write("\n".join(script_lines))

# 저장된 스크립트 내용 출력
with open(output_script_path, "r", encoding="utf-8") as f:
    print(f.read())

# 영상 제작 로직 (예시: 실제로는 ffmpeg 등 활용)
# 이 부분은 프로젝트 상황에 따라 구현 필요

# Supabase에 영상 등록
included_ids = ",".join(str(n["id"]) for n in news_list)

insert_url = f"{SUPABASE_URL}/rest/v1/newsletter_videos"
insert_payload = {
    "subject": first_subject,
    "included_newsletter_ids": included_ids
}
insert_res = requests.post(insert_url, json=insert_payload, headers=headers)

if insert_res.status_code in [200, 201]:
    print(f"newsletter_videos 테이블에 등록 완료: {first_subject}")
else:
    print(f"등록 실패: {insert_res.status_code} - {insert_res.text}")
