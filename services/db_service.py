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

# ══════════════════════════════════════════════════
#  cash_flows CRUD (입출금 이력)
# ══════════════════════════════════════════════════
def get_all_cash_flows():
    res = supabase.table("cash_flows").select("*").order("date", desc=False).execute()
    return res.data

def add_cash_flow(data: dict):
    supabase.table("cash_flows").insert(data).execute()

def delete_cash_flow(id: int):
    supabase.table("cash_flows").delete().eq("id", id).execute()

def get_cash_summary():
    """
    총 입금액, 총 출금액, 순수 현금 투자액 계산
    반환: {"total_deposit", "total_withdrawal", "net_cash"}
    """
    flows = get_all_cash_flows()
    total_deposit    = sum(float(f["amount"]) for f in flows if f["type"] == "deposit")
    total_withdrawal = sum(float(f["amount"]) for f in flows if f["type"] == "withdrawal")
    return {
        "total_deposit":    total_deposit,
        "total_withdrawal": total_withdrawal,
        "net_cash":         total_deposit - total_withdrawal,
    }

# ══════════════════════════════════════════════════
#  watchlist CRUD (즐겨찾기 종목)
# ══════════════════════════════════════════════════
def get_watchlist():
    res = supabase.table("watchlist").select("*").order("created_at", desc=False).execute()
    return res.data

def add_watchlist(ticker: str, name: str):
    # 중복 체크
    existing = supabase.table("watchlist").select("id").eq("ticker", ticker).execute()
    if not existing.data:
        supabase.table("watchlist").insert({"ticker": ticker, "name": name}).execute()

def delete_watchlist(id: int):
    supabase.table("watchlist").delete().eq("id", id).execute()

# ══════════════════════════════════════════════════
#  종목 수정 헬퍼
# ══════════════════════════════════════════════════
def get_transactions_by_ticker(ticker: str):
    """특정 티커의 모든 거래 이력 반환"""
    res = supabase.table("transactions").select("*") \
        .eq("ticker", ticker).order("date", desc=False).execute()
    return res.data

def delete_transactions_by_ticker(ticker: str):
    """특정 티커의 모든 거래 이력 삭제 (종목 전체 삭제)"""
    supabase.table("transactions").delete().eq("ticker", ticker).execute()

def adjust_holding_qty(ticker: str, name: str, market: str,
                       is_etf: bool, current_qty: float,
                       new_qty: float, avg_price: float):
    """
    수량 변경 — 차이만큼 buy/sell 자동 추가
    new_qty > current_qty : 차이만큼 buy 추가
    new_qty < current_qty : 차이만큼 sell 추가
    """
    diff = new_qty - current_qty
    if abs(diff) < 0.0001:
        return
    tx_type = "buy" if diff > 0 else "sell"
    add_transaction({
        "ticker":  ticker,
        "name":    name,
        "market":  market,
        "is_etf":  is_etf,
        "type":    tx_type,
        "qty":     abs(diff),
        "price":   avg_price,
        "date":    str(date.today()),
    })

def adjust_holding_avg_price(ticker: str, new_avg: float):
    """
    평균단가 변경 — 해당 티커의 모든 buy 거래 단가를 비율로 조정
    (전체 매수금액을 유지하면서 단가만 새로 설정)
    실제로는 buy 이력 전체를 합산 후 단가를 균일하게 재설정
    """
    txs = get_transactions_by_ticker(ticker)
    buy_txs = [t for t in txs if t["type"] == "buy"]
    if not buy_txs:
        return
    total_qty = sum(float(t["qty"]) for t in buy_txs)
    if total_qty <= 0:
        return
    # buy 거래 단가를 새로운 평균단가로 일괄 업데이트
    for t in buy_txs:
        update_transaction(t["id"], {"price": new_avg})
