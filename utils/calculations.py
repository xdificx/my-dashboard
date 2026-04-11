def calculate_portfolio_row(h, price, FX):
    cur = round(price * FX) if h["market"] == "US" else round(price)
    avg = round(h["avg"] * FX) if h["market"] == "US" else round(h["avg"])
    val = cur * h["qty"]
    pnl = (cur - avg) * h["qty"]
    ret = (cur - avg) / avg * 100 if avg > 0 else 0

    return {
        "종목": h["name"],
        "현재가": f"{price:.2f}",
        "수량": h["qty"],
        "평가금액(원)": f"{val:,.0f}",
        "평가손익(원)": f"{pnl:+,.0f}",
        "수익률(%)": round(ret, 2)
    }
