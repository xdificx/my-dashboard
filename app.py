import streamlit as st
from services.data_service import get_ticker_data
from utils.calculations import calculate_portfolio_row
from components.portfolio_table import render_portfolio_table

st.set_page_config(page_title="내 투자 대시보드", layout="wide")

# 보유 종목 초기값
if "holdings" not in st.session_state:
    st.session_state.holdings = [
        {"ticker": "005930.KS", "name": "삼성전자", "qty": 20, "avg": 72000, "market": "KR"},
        {"ticker": "AAPL", "name": "Apple", "qty": 5, "avg": 172.0, "market": "US"},
    ]

st.title("📊 내 투자 대시보드")

# 환율
fx = get_ticker_data("USDKRW=X")
FX = fx["price"] if fx.get("ok") else 1300

# 데이터 계산
rows = []
for h in st.session_state.holdings:
    d = get_ticker_data(h["ticker"])
    if d["ok"]:
        rows.append(calculate_portfolio_row(h, d["price"], FX))

# 테이블 출력
render_portfolio_table(rows)
