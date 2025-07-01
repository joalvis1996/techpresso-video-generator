import os

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")
print(SUPABASE_URL)
print(SUPABASE_API_KEY)

HEADERS = {
    "apikey": SUPABASE_API_KEY,
    "Authorization": f"Bearer {SUPABASE_API_KEY}"
}

print("HEADERS:", HEADERS)
print("SUPABASE_URL:", SUPABASE_URL)