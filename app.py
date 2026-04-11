import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from datetime import datetime, timedelta
import time

st.set_page_config(
    page_title="내 투자 대시보드",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ====================== 다크모드 + 스타일 ======================
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #fafafa; }
    .metric-card { background-color: #1a1f2e; padding: 15px; border-radius: 10px; }
    .up { color: #ff4d4d; }
    .down { color: #4d9eff; }
</style>
""", unsafe_allow_html=True)

# ====================== 세션 상태 초기화 ======================
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
        price = info.last_price or info.current_price
        prev = info.previous_close
        if price and prev:
            chg = (price - prev) / prev * 100
            return {
                "price": round(price, 2),
                "chg": round(chg, 2),
                "diff": round(price - prev, 2),
                "ok": True
            }
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
    
    refresh_option = st.selectbox("자동 새로고침", 
                                  ["30초", "1분", "5분", "수동"], index=2)
    
    st.divider()
    st.subheader("📋 보유 종목 관리")
    
    # 종목 추가
    with st.expander("➕ 종목 추가"):
        col1, col2 = st.columns(2)
        new_ticker = col1.text_input("티커", placeholder="005930.KS")
        new_name = col2.text_input("종목명")
        col3, col4 = st.columns(2)
        new_qty = col3.number_input("수량", min_value=1, value=10)
        new_avg = col4.number_input("평균단가", value=50000.0)
        market = st.selectbox("시장", ["KR", "US"])
        if st.button("추가하기"):
            st.session_state.holdings.append({
                "ticker": new_ticker, "name": new_name, "qty": int(new_qty),
                "avg": float(new_avg), "market": market
            })
            st.success("추가되었습니다!")
            st.rerun()

    # 종목 목록 편집
    for i, h in enumerate(st.session_state.holdings):
        with st.expander(f"{h['name']} ({h['ticker']})"):
            col1, col2 = st.columns(2)
            h['qty'] = col1.number_input("수량", value=h['qty'], key=f"qty_{i}")
            h['avg'] = col2.number_input("평균단가", value=h['avg'], key=f"avg_{i}")
            if st.button("🗑️ 삭제", key=f"del_{i}"):
                st.session_state.holdings.pop(i)
                st.rerun()

    st.divider()
    st.caption(f"마지막 갱신: {datetime.now().strftime('%H:%M:%S')}")

# ====================== 메인 ======================
tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "💼 보유종목", "📈 차트분석", "📡 데이터상태"])

with tab1:  # Overview
    st.title("📊 내 투자 대시보드")
    
    fx = get_ticker_data("USDKRW=X")
    FX = fx["price"] if fx["ok"] else 1330.0

    # 지수 및 매크로
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**🇰🇷 국내 지수**")
        for t, l in [("^KS11", "KOSPI"), ("^KQ11", "KOSDAQ"), ("^KS200", "KOSPI200")]:
            d = get_ticker_data(t)
            if d["ok"]:
                st.metric(l, f"{d['price']:,.0f}", f"{d['chg']:+.2f}%")
    
    with col2:
        st.markdown("**🌎 해외 지수**")
        for t, l in [("^GSPC", "S&P500"), ("^IXIC", "나스닥"), ("^DJI", "다우")]:
            d = get_ticker_data(t)
            if d["ok"]:
                st.metric(l, f"{d['price']:,.0f}", f"{d['chg']:+.2f}%")
    
    with col3:
        st.markdown("**📡 매크로**")
        for t, l in [("USDKRW=X", "원/달러"), ("^TNX", "10년국채"), ("^VIX", "VIX")]:
            d = get_ticker_data(t)
            if d["ok"]:
                st.metric(l, f"{d['price']:.2f}", f"{d['chg']:+.2f}%")

    st.divider()
    
    # 포트폴리오 요약
    st.subheader("💰 포트폴리오 요약")
    total_val = total_cost = total_pnl = 0
    rows = []

    for h in st.session_state.holdings:
        d = get_ticker_data(h["ticker"])
        if d["ok"]:
            price = d["price"]
            cur_krw = round(price * FX) if h["market"] == "US" else round(price)
            avg_krw = round(h["avg"] * FX) if h["market"] == "US" else round(h["avg"])
            
            val = cur_krw * h["qty"]
            pnl = (cur_krw - avg_krw) * h["qty"]
            ret = (cur_krw - avg_krw) / avg_krw * 100 if avg_krw else 0
            
            total_val += val
            total_cost += avg_krw * h["qty"]
            total_pnl += pnl
            
            rows.append({
                "종목": h["name"], "현재가": f"{price:.2f}", "수량": h["qty"],
                "평가금액": f"{val:,.0f}", "평가손익": f"{pnl:+,.0f}",
                "수익률": f"{ret:+.2f}%"
            })

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총 투자원금", f"{total_cost:,.0f}원")
    c2.metric("총 평가금액", f"{total_val:,.0f}원")
    c3.metric("총 평가손익", f"{total_pnl:+,.0f}원", delta=f"{total_pnl/total_cost*100:+.2f}%" if total_cost else 0)
    c4.metric("총 수익률", f"{(total_pnl/total_cost*100 if total_cost else 0):+.2f}%")

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

with tab2:  # 보유종목 상세
    st.subheader("💼 보유 종목 상세")
    for h in st.session_state.holdings:
        with st.expander(f"📍 {h['name']} ({h['ticker']})"):
            d = get_ticker_data(h["ticker"])
            if d["ok"]:
                st.metric("현재가", f"{d['price']:,}", f"{d['chg']:+.2f}%")

with tab3:  # 차트분석
    st.subheader("📈 종목 차트 분석")
    selected = st.selectbox("종목 선택", [h["name"] for h in st.session_state.holdings])
    ticker = next(h["ticker"] for h in st.session_state.holdings if h["name"] == selected)
    period = st.selectbox("기간", ["1mo", "3mo", "6mo", "1y"], index=3)
    
    hist = get_history(ticker, period)
    if not hist.empty:
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                           row_heights=[0.5, 0.2, 0.3], vertical_spacing=0.05)
        
        # 캔들차트
        fig.add_trace(go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'],
                                    low=hist['Low'], close=hist['Close'], name="Price"), row=1, col=1)
        
        # 거래량
        fig.add_trace(go.Bar(x=hist.index, y=hist['Volume'], name="Volume", marker_color="#4d9eff"), row=2, col=1)
        
        # RSI (간단 버전)
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        fig.add_trace(go.Scatter(x=hist.index, y=rsi, name="RSI", line=dict(color="orange")), row=3, col=1)
        
        fig.update_layout(height=800, template="plotly_dark", title=f"{selected} 차트")
        st.plotly_chart(fig, use_container_width=True)

with tab4:  # 데이터 상태 (기존 파일 유지)
    st.subheader("📡 데이터 소스 상태")
    # (기존 2_파일 내용을 간단히 포함하거나 필요시 별도 페이지 유지 추천)

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
