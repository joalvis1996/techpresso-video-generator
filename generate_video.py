import os

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")
print(SUPABASE_URL)
print(SUPABASE_API_KEY)


print("HEADERS:", HEADERS)
print("Request URL:", f"{SUPABASE_URL}/rest/v1/news?video_url=is.null&select=*")
print("ROWS:", rows)
