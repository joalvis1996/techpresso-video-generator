from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
  "https://www.googleapis.com/auth/youtube.upload",
   "https://www.googleapis.com/auth/youtube.readonly"
]

flow = InstalledAppFlow.from_client_secrets_file(
  "client_secret_953613797458-796r9qoc0pmsdq2h2ifi0r4qctdld0ln.apps.googleusercontent.com.json",
  SCOPES
)
creds = flow.run_local_server(port=0)   # 로컬 서버로 브라우저 열어줌

with open("token.json", "w") as token:
    token.write(creds.to_json())