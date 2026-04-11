from supabase import create_client

SUPABASE_URL = "https://iadwpshbyphyxnearpir.supabase.co"
SUPABASE_KEY = "sb_publishable_9hYxK_tOLq4AuQ2FScS7vw_kSjdNzzT"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
