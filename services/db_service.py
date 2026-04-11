from services.supabase_client import supabase
from datetime import datetime, date

# ══════════════════════════════════════════════════
#  transactions CRUD
# ══════════════════════════════════════════════════
def get_all_transactions():
    res = supabase.table("transactions").select("*").order("date", desc=False).execute()
    return res.data

def add_transaction(data: dict):
    supabase.table("transactions").insert(data).execute()

def delete_transaction(id: int):
    supabase.table("transactions").delete().eq("id", id).execute()

def update_transaction(id: int, data: dict):
    supabase.table("transactions").update(data).eq("id", id).execute()

# ══════════════════════════════════════════════════
#  현재 보유 종목 계산 (매수 - 매도)
# ══════════════════════════════════════════════════
def get_current_holdings(transactions=None):
    """
    매수/매도 이력으로부터 현재 보유 종목 계산
    반환: [{"ticker","name","market","is_etf","qty","avg_price"}, ...]
    """
    if transactions is None:
        transactions = get_all_transactions()

    summary = {}
    for t in transactions:
        key = t["ticker"]
        if key not in summary:
            summary[key] = {
                "ticker":     t["ticker"],
                "name":       t["name"],
                "market":     t["market"],
                "is_etf":     t.get("is_etf", False),
                "buy_qty":    0.0,
                "buy_amount": 0.0,
                "sell_qty":   0.0,
            }
        if t["type"] == "buy":
            summary[key]["buy_qty"]    += float(t["qty"])
            summary[key]["buy_amount"] += float(t["qty"]) * float(t["price"])
        elif t["type"] == "sell":
            summary[key]["sell_qty"]   += float(t["qty"])

    holdings = []
    for key, s in summary.items():
        remain = s["buy_qty"] - s["sell_qty"]
        if remain > 0.0001:
            avg = s["buy_amount"] / s["buy_qty"] if s["buy_qty"] > 0 else 0
            holdings.append({
                "ticker":    s["ticker"],
                "name":      s["name"],
                "market":    s["market"],
                "is_etf":    s["is_etf"],
                "qty":       remain,
                "avg_price": round(avg, 2),
                "avg":       round(avg, 2),  # calculations.py 호환
            })
    return holdings

# ══════════════════════════════════════════════════
#  매도 완료 종목 계산
# ══════════════════════════════════════════════════
def get_closed_positions(transactions=None):
    """
    완전히 매도 완료된 종목 및 실현 손익 계산
    반환: [{"ticker","name","market","qty","avg_buy","avg_sell",
             "realized_pnl","return_pct","hold_days",...}, ...]
    """
    if transactions is None:
        transactions = get_all_transactions()

    summary = {}
    for t in transactions:
        key = t["ticker"]
        if key not in summary:
            summary[key] = {
                "ticker":      t["ticker"],
                "name":        t["name"],
                "market":      t["market"],
                "buy_qty":     0.0, "buy_amount":  0.0,
                "sell_qty":    0.0, "sell_amount": 0.0,
                "first_buy":   None, "last_sell":  None,
            }
        s = summary[key]
        if t["type"] == "buy":
            s["buy_qty"]    += float(t["qty"])
            s["buy_amount"] += float(t["qty"]) * float(t["price"])
            d = str(t["date"])
            if s["first_buy"] is None or d < s["first_buy"]:
                s["first_buy"] = d
        elif t["type"] == "sell":
            s["sell_qty"]    += float(t["qty"])
            s["sell_amount"] += float(t["qty"]) * float(t["price"])
            d = str(t["date"])
            if s["last_sell"] is None or d > s["last_sell"]:
                s["last_sell"] = d

    closed = []
    for key, s in summary.items():
        remain = s["buy_qty"] - s["sell_qty"]
        if remain < 0.0001 and s["sell_qty"] > 0:
            avg_buy  = s["buy_amount"]  / s["buy_qty"]  if s["buy_qty"]  > 0 else 0
            avg_sell = s["sell_amount"] / s["sell_qty"] if s["sell_qty"] > 0 else 0
            pnl      = (avg_sell - avg_buy) * s["sell_qty"]
            ret      = (avg_sell - avg_buy) / avg_buy * 100 if avg_buy > 0 else 0
            hold_days = 0
            if s["first_buy"] and s["last_sell"]:
                hold_days = (
                    datetime.strptime(s["last_sell"], "%Y-%m-%d") -
                    datetime.strptime(s["first_buy"],  "%Y-%m-%d")
                ).days
            closed.append({
                "ticker":       s["ticker"],
                "name":         s["name"],
                "market":       s["market"],
                "qty":          s["sell_qty"],
                "avg_buy":      round(avg_buy,  2),
                "avg_sell":     round(avg_sell, 2),
                "realized_pnl": round(pnl),
                "return_pct":   round(ret, 2),
                "hold_days":    hold_days,
                "first_buy":    s["first_buy"],
                "last_sell":    s["last_sell"],
            })
    return closed

# ══════════════════════════════════════════════════
#  하위 호환 (app.py, chart.py 에서 사용)
# ══════════════════════════════════════════════════
def get_all_holdings():
    return get_current_holdings()
