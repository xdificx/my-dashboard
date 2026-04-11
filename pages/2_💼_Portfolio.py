import streamlit as st
from services.db_service import get_all_holdings, add_holding, delete_holding, update_holding
from services.data_service import get_ticker_data

st.title("💼 Portfolio")

holdings = get_all_holdings()

# ➕ 추가
with st.expander("➕ 종목 추가"):
    ticker = st.text_input("티커")
    name = st.text_input("종목명")
    qty = st.number_input("수량", min_value=1, value=1)
    avg = st.number_input("평균단가", value=0.0)
    market = st.selectbox("시장", ["KR", "US"])

    if st.button("추가"):
        add_holding({
            "ticker": ticker,
            "name": name,
            "qty": qty,
            "avg": avg,
            "market": market
        })
        st.rerun()

# 📋 목록
for i, h in enumerate(holdings):
    with st.expander(f"{h['name']} ({h['ticker']})"):
        price = get_ticker_data(h["ticker"])

        if price["ok"]:
            st.metric("현재가", price["price"], f"{price['chg']:+.2f}%")

        qty = st.number_input("수량", value=h["qty"], key=f"qty_{i}")
        avg = st.number_input("평단", value=h["avg"], key=f"avg_{i}")

        if st.button("수정", key=f"update_{i}"):
            update_holding(h["id"], qty, avg)
            st.rerun()

        if st.button("삭제", key=f"del_{i}"):
            delete_holding(h["id"])
            st.rerun()
