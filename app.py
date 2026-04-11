import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import time

# ====================== 페이지 설정 ======================
st.set_page_config(
    page_title="내 투자 대시보드",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ====================== 다크모드 스타일 ======================
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #fafafa; }
    .up { color: #ff4d4d; }
    .down { color: #4d9eff; }
</style>
""", unsafe_allow_html=True)

# ====================== 세션 상태 ======================
if "holdings" not in st.session_state:
    st.session_state.holdings = [
        {"ticker": "005930.KS", "name": "삼성전자",    "qty": 20,  "avg": 72000,  "market": "KR"},
        {"ticker": "035720.KQ", "name": "카카오",      "qty": 10,  "avg": 58000,  "market": "KR"},
        {"ticker": "000660.KS", "name": "SK하이닉스",  "qty":  5,  "avg": 130000, "market": "KR"},
        {"ticker": "AAPL",      "name": "Apple",       "qty":  5,  "avg": 172.0,  "market": "US"},
        {"ticker": "SCHD",      "name": "SCHD ETF",    "qty": 10,  "avg": 77.0,   "market": "US"},
    ]

# ====================== 데이터 함수 ======================
@st.cache_data(ttl=60)
def get_ticker_data(ticker: str):
    try:
        stock = yf.Ticker(ticker)
        info = stock.fast_info
        price = info.last_price or getattr(info, 'current_price', None)
        prev = info.previous_close
        if price and prev:
            chg = (price - prev) / prev * 100
            return {"price": round(price, 2), "chg": round(chg, 2), "diff": round(price - prev, 2), "ok": True}
    except:
        pass
    return {"price": None, "chg": None, "diff": None, "ok": False}

@st.cache_data(ttl=300)
def get_history(ticker: str, period="1y"):
    try:
        return yf.download(ticker, period=period, interval="1d", progress=False)
    except:
        return pd.DataFrame()

# ====================== 사이드바 ======================
with st.sidebar:
    st.title("⚙️ 설정")
    refresh_option = st.selectbox("자동 새로고침", ["30초", "1분", "5분", "수동"], index=2)
    
    st.divider()
    st.subheader("📋 보유 종목 관리")
    
    with st.expander("➕ 새 종목 추가"):
        col1, col2 = st.columns(2)
        new_ticker = col1.text_input("티커", placeholder="005930.KS")
        new_name = col2.text_input("종목명", placeholder="삼성전자")
        col3, col4 = st.columns(2)
        new_qty = col3.number_input("수량", min_value=1, value=10)
        new_avg = col4.number_input("평균단가", value=50000.0)
        market = st.selectbox("시장", ["KR", "US"])
        if st.button("추가하기"):
            if new_ticker and new_name:
                st.session_state.holdings.append({
                    "ticker": new_ticker, "name": new_name, "qty": int(new_qty),
                    "avg": float(new_avg), "market": market
                })
                st.success("추가되었습니다!")
                st.rerun()

    for i, h in enumerate(st.session_state.holdings):
        with st.expander(f"{h['name']} ({h['ticker']})"):
            col1, col2 = st.columns(2)
            h['qty'] = col1.number_input("수량", value=h['qty'], key=f"qty_{i}")
            h['avg'] = col2.number_input("평균단가", value=h['avg'], key=f"avg_{i}")
            if st.button("🗑️ 삭제", key=f"del_{i}"):
                st.session_state.holdings.pop(i)
                st.rerun()

# ====================== 메인 ======================
tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "💼 보유종목", "📈 차트분석", "📡 데이터상태"])

with tab1:
    st.title("📊 내 투자 대시보드")
    
    fx_data = get_ticker_data("USDKRW=X")
    FX = fx_data["price"] if fx_data.get("ok") else 1330.0

    # 지수 & 매크로
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**🇰🇷 국내 지수**")
        for t, name in [("^KS11","KOSPI"), ("^KQ11","KOSDAQ"), ("^KS200","KOSPI200")]:
            d = get_ticker_data(t)
            if d["ok"]: st.metric(name, f"{d['price']:,.0f}", f"{d['chg']:+.2f}%")
    with c2:
        st.markdown("**🌎 해외 지수**")
        for t, name in [("^GSPC","S&P500"), ("^IXIC","나스닥"), ("^DJI","다우존스")]:
            d = get_ticker_data(t)
            if d["ok"]: st.metric(name, f"{d['price']:,.0f}", f"{d['chg']:+.2f}%")
    with c3:
        st.markdown("**📡 매크로**")
        for t, name in [("USDKRW=X","원/달러"), ("^TNX","10년국채"), ("^VIX","VIX")]:
            d = get_ticker_data(t)
            if d["ok"]: st.metric(name, f"{d['price']:.2f}", f"{d['chg']:+.2f}%")

    st.divider()
    st.subheader("💼 보유 종목 수익률")

    rows = []
    for h in st.session_state.holdings:
        d = get_ticker_data(h["ticker"])
        if d["ok"]:
            price = d["price"]
            cur = round(price * FX) if h["market"] == "US" else round(price)
            avg = round(h["avg"] * FX) if h["market"] == "US" else round(h["avg"])
            val = cur * h["qty"]
            pnl = (cur - avg) * h["qty"]
            ret = (cur - avg) / avg * 100 if avg > 0 else 0

            rows.append({
                "종목": h["name"],
                "현재가": f"{price:.2f}",
                "수량": h["qty"],
                "평가금액(원)": f"{val:,.0f}",
                "평가손익(원)": f"{pnl:+,.0f}",
                "수익률(%)": round(ret, 2)
            })

    df = pd.DataFrame(rows)

    def color_ret(v):
        if isinstance(v, (int, float)):
            return "color:#e24b4a;
