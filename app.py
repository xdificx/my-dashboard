import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time

from services.data_service import get_ticker_data, get_history
from services.db_service import get_all_holdings, add_holding, delete_holding, update_holding

st.set_page_config(
    page_title="내 투자 대시보드",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ====================== DB 데이터 ======================
holdings = get_all_holdings()

# ====================== 데이터 함수 ======================
@st.cache_data(ttl=60)
def get_fx():
    fx = get_ticker_data("USDKRW=X")
    return fx["price"] if fx.get("ok") else 1330.0

# ====================== 사이드바 ======================
with st.sidebar:
    st.title("⚙️ 설정")
    refresh_option = st.selectbox("자동 새로고침", ["30초", "1분", "5분", "수동"], index=2)
    
    st.divider()
    st.subheader("📋 보유 종목 관리")
    
    with st.expander("➕ 새 종목 추가"):
        col1, col2 = st.columns(2)
        new_ticker = col1.text_input("티커")
        new_name = col2.text_input("종목명")
        col3, col4 = st.columns(2)
        new_qty = col3.number_input("수량", min_value=1, value=10)
        new_avg = col4.number_input("평균단가", value=50000.0)
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
                st.success(f"{new_name} 추가 완료!")
                st.rerun()

    for i, h in enumerate(holdings):
        with st.expander(f"{h['name']} ({h['ticker']})"):
            col1, col2 = st.columns(2)
            qty = col1.number_input("수량", value=h["qty"], key=f"qty_{i}")
            avg = col2.number_input("평균단가", value=h["avg"], key=f"avg_{i}")

            if st.button("수정", key=f"update_{i}"):
                update_holding(h["id"], qty, avg)
                st.rerun()

            if st.button("🗑️ 삭제", key=f"del_{i}"):
                delete_holding(h["id"])
                st.rerun()

# ====================== 메인 ======================
tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "💼 보유종목", "📈 차트분석", "📡 데이터상태"])

# ====================== Overview ======================
with tab1:
    st.title("📊 내 투자 대시보드")
    
    FX = get_fx()

    c1, c2, c3 = st.columns(3)
    with c1:
        st.subheader("🇰🇷 국내 지수")
        for t, n in [("^KS11", "KOSPI"), ("^KQ11", "KOSDAQ"), ("^KS200", "KOSPI200")]:
            d = get_ticker_data(t)
            if d["ok"]: st.metric(n, f"{d['price']:,.0f}", f"{d['chg']:+.2f}%")
    
    with c2:
        st.subheader("🌎 해외 지수")
        for t, n in [("^GSPC", "S&P500"), ("^IXIC", "나스닥"), ("^DJI", "다우존스")]:
            d = get_ticker_data(t)
            if d["ok"]: st.metric(n, f"{d['price']:,.0f}", f"{d['chg']:+.2f}%")
    
    with c3:
        st.subheader("📡 매크로 지표")
        for t, n in [("USDKRW=X", "원/달러"), ("^TNX", "10년국채"), ("^VIX", "VIX")]:
            d = get_ticker_data(t)
            if d["ok"]: st.metric(n, f"{d['price']:.2f}", f"{d['chg']:+.2f}%")

    st.divider()
    st.subheader("💼 보유 종목 수익률")

    rows = []
    for h in holdings:
        d = get_ticker_data(h["ticker"])
        if d["ok"]:
            rows.append({
                "종목": h["name"],
                "현재가": d["price"],
                "수량": h["qty"],
                "평가금액(원)": int(d["price"] * h["qty"]),
                "수익률(%)": round((d["price"] - h["avg"]) / h["avg"] * 100, 2)
            })

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ====================== 보유종목 ======================
with tab2:
    st.subheader("💼 보유 종목 상세")
    for h in holdings:
        d = get_ticker_data(h["ticker"])
        if d["ok"]:
            st.metric(h["name"], f"{d['price']}", f"{d['chg']:+.2f}%")

# ====================== 차트 ======================
with tab3:
    st.subheader("📈 차트 분석")
    if holdings:
        selected = st.selectbox("종목 선택", [h["name"] for h in holdings])
        ticker = next(h["ticker"] for h in holdings if h["name"] == selected)
        hist = get_history(ticker, "1y")
        if not hist.empty:
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True)
            fig.add_trace(go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close']), row=1, col=1)
            fig.add_trace(go.Bar(x=hist.index, y=hist['Volume']), row=2, col=1)
            st.plotly_chart(fig, use_container_width=True)

# ====================== 데이터 상태 ======================
with tab4:
    st.info("📡 데이터 상태 페이지는 유지됨")

# ====================== 자동 새로고침 ======================
if refresh_option == "30초":
    time.sleep(30)
    st.rerun()
elif refresh_option == "1분":
    time.sleep(60)
    st.rerun()
elif refresh_option == "5분":
    time.sleep(300)
    st.rerun()
    
