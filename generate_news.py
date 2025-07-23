import os
import requests

# 🔐 환경 변수에서 Supabase 정보 가져오기
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")

if not SUPABASE_URL or not SUPABASE_API_KEY:
    raise Exception("❌ SUPABASE_URL 또는 SUPABASE_API_KEY 환경변수가 설정되지 않았습니다.")

headers = {
    "apikey": SUPABASE_API_KEY,
    "Authorization": f"Bearer {SUPABASE_API_KEY}"
}

# === 1) Supabase에서 아직 영상화되지 않은 subject 그룹 가져오기 ===
query = (
    f"{SUPABASE_URL}/rest/v1/newsletter?"
    "select=id,subject,news_style_content&"
    "subject=not.is.null&"
    "subject=not.in.(select+subject+from+newsletter_videos)"
)
response = requests.get(query, headers=headers)

if response.status_code != 200:
    raise Exception(f"❌ Supabase 요청 실패: {response.status_code} {response.text}")

news_items = response.json()

if not news_items:
    print("✅ 영상화되지 않은 새로운 subject 뉴스가 없습니다.")
    exit()

print("✅ 확인된 뉴스 영상" , news_items)
exit()

# === 2) subject별로 뉴스 그룹 묶기 ===
grouped_by_subject = {}
for item in news_items:
    subject = item["subject"]
    grouped_by_subject.setdefault(subject, []).append(item)

# === 3) 각 subject별로 하나의 스크립트 생성 ===
for subject, items in grouped_by_subject.items():
    script_lines = []
    script_lines.append("📺 최신 IT/테크 뉴스입니다.\n")

    # 카테고리별 뉴스 정리
    grouped_by_category = {}
    for item in items:
        category = item.get("category", "기타")
        grouped_by_category.setdefault(category, []).append(item["news_style_content"])

    for category, contents in grouped_by_category.items():
        script_lines.append(f"\n📢 [{category} 뉴스]")
        for idx, news in enumerate(contents, 1):
            script_lines.append(f"\n[{idx}] {news}")
            if idx < len(contents):
                script_lines.append("다음 뉴스입니다.\n")

    script_lines.append("\n이상으로 주요 뉴스를 전해드렸습니다. 감사합니다.")

    # 💾 subject 기반으로 파일 저장
    filename_safe_subject = subject.replace(" ", "_").replace("/", "_")
    output_path = f"scripts/{filename_safe_subject}.txt"
    os.makedirs("scripts", exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(script_lines))

    print(f"✅ 뉴스 스크립트 저장 완료: {output_path}")
