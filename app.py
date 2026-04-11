import streamlit as st
from services.data_service import get_ticker_data
from utils.calculations import calculate_portfolio_row
from components.portfolio_table import render_portfolio_table

# ✅ Supabase 연결
from services.db_service import get_all_holdings, add_holding, delete_holding

st.set_page_config(page_title="내 투자 대시보드", layout="wide")

st.title("📊 내 투자 대시보드")

# ✅ DB에서 데이터 불러오기
holdings = get_all_holdings()

# ======================
# ➕ 종목 추가 UI
# ======================
st.subheader("➕ 종목 추가")

col1, col2 = st.columns(2)
new_ticker = col1.text_input("티커")
new_name = col2.text_input("종목명")

col3, col4 = st.columns(2)
new_qty = col3.number_input("수량", min_value=1, value=1)
new_avg = col4.number_input("평균단가", value=0.0)

market = st.selectbox("시장", ["KR", "US"])

if st.button("추가하기"):
    if new_ticker and new_name:
        add_holding({
            "ticker": new_ticker,
            "name": new_name,
            "qty": int(new_qty),
            "avg": float(new_avg),
            "market": market
        })
        st.success("추가 완료")
        st.rerun()

st.divider()

# ======================
# 💱 환율
# ======================
fx = get_ticker_data("USDKRW=X")
FX = fx["price"] if fx.get("ok") else 1300

# ======================
# 📊 데이터 계산
# ======================
rows = []
for h in holdings:
    d = get_ticker_data(h["ticker"])
    if d["ok"]:
        rows.append(calculate_portfolio_row(h, d["price"], FX))

# ======================
# 📋 테이블 출력
# ======================
render_portfolio_table(rows)

# ======================
# 🗑️ 삭제 기능
# ======================
st.subheader("🗑️ 종목 삭제")

for h in holdings:
    col1, col2 = st.columns([3, 1])
    col1.write(f"{h['name']} ({h['ticker']})")
    
    if col2.button("삭제", key=h["id"]):
        delete_holding(h["id"])
        st.rerun()
