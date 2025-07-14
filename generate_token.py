import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# 👇 필요한 스코프 설정
SCOPES = [
  "https://www.googleapis.com/auth/youtube.upload",
  "https://www.googleapis.com/auth/youtube.readonly",
  "https://www.googleapis.com/auth/youtube"
]

def main():
    creds = None

    # 기존 토큰 로드
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    # 없거나 만료되었으면 새로 발급
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "client_secret_953613797458-vshdscpkvaukbl13rpvg7q6p8ct9tu9v.apps.googleusercontent.com.json",
                SCOPES
            )
            # ✔️ run_local_server가 최신 버전에서 권장됨
            creds = flow.run_local_server(port=0)

        # 토큰 저장
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    print("✅ OAuth token 생성 완료!")

if __name__ == "__main__":
    main()
