from services.supabase_client import supabase

def get_all_holdings():
    res = supabase.table("holdings").select("*").execute()
    return res.data

def add_holding(data):
    supabase.table("holdings").insert(data).execute()

def delete_holding(id):
    supabase.table("holdings").delete().eq("id", id).execute()

def update_holding(id, qty, avg):
    supabase.table("holdings").update({
        "qty": qty,
        "avg": avg
    }).eq("id", id).execute()
