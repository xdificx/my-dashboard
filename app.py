import streamlit as st
import yfinance as yf
import pandas as pd
from pykrx import stock
from datetime import datetime, timedelta
import time

# ─────────────────────────────────────────
#  페이지 설정
# ─────────────────────────────────────────
st.set_page_config(
    page_title="내 투자 대시보드",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────
#  보유 종목 — 여기만 수정하면 됩니다
#  market: "KR" = 국내, "US" = 해외
# ─────────────────────────────────────────
MY_HOLDINGS = [
    {"ticker": "005930", "name": "삼성전자",     "qty": 20,  "avg": 72000,  "market": "KR"},
    {"ticker": "035720", "name": "카카오",        "qty": 10,  "avg": 58000,  "market": "KR"},
    {"ticker": "000660", "name": "SK하이닉스",    "qty":  5,  "avg": 130000, "market": "KR"},
    {"ticker": "AAPL",   "name": "Apple",         "qty":  5,  "avg": 172.0,  "market": "US"},
    {"ticker": "SCHD",   "name": "SCHD ETF",      "qty": 10,  "avg": 77.0,   "market": "US"},
]

# ─────────────────────────────────────────
#  환율 (yfinance로 실시간 조회)
# ─────────────────────────────────────────
@st.cache_data(ttl=300)
def get_fx_rate():
    try:
        fx = yf.Ticker("USDKRW=X").fast_info.last_price
        return round(fx, 2)
    except:
        return 1330.0

# ─────────────────────────────────────────
#  지수 데이터
# ─────────────────────────────────────────
@st.cache_data(ttl=300)
def get_index_data():
    tickers = {
        "^KS11":     "KOSPI",
        "^KQ11":     "KOSDAQ",
        "^GSPC":     "S&P 500",
        "^IXIC":     "나스닥",
        "^DJI":      "다우존스",
        "^TNX":      "미 10년 국채",
        "DX-Y.NYB":  "달러 인덱스",
        "USDKRW=X":  "원/달러 환율",
        "GC=F":      "금 선물",
        "CL=F":      "WTI 원유",
    }
    results = {}
    for ticker, label in tickers.items():
        try:
            info  = yf.Ticker(ticker).fast_info
            price = info.last_price
            prev  = info.previous_close
            chg   = (price - prev) / prev * 100
            results[label] = {"price": price, "chg": chg, "ticker": ticker}
        except:
            results[label] = {"price": None, "chg": None, "ticker": ticker}
    return results

# ─────────────────────────────────────────
#  국내 종목 현재가 (pykrx)
# ─────────────────────────────────────────
@st.cache_data(ttl=300)
def get_kr_price(ticker: str):
    today = datetime.today()
    for i in range(5):  # 최근 5 영업일 중 데이터 있는 날 사용
        d = (today - timedelta(days=i)).strftime("%Y%m%d")
        try:
            df = stock.get_market_ohlcv(d, d, ticker)
            if not df.empty:
                return int(df["종가"].iloc[-1])
        except:
            pass
    return None

# ─────────────────────────────────────────
#  해외 종목 현재가 (yfinance)
# ─────────────────────────────────────────
@st.cache_data(ttl=300)
def get_us_price(ticker: str):
    try:
        return round(yf.Ticker(ticker).fast_info.last_price, 2)
    except:
        return None

# ─────────────────────────────────────────
#  사이드바
# ─────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ 설정")
    auto_refresh = st.toggle("자동 갱신 (5분)", value=True)
    st.markdown("---")
    st.markdown("**종목 수정 방법**")
    st.markdown(
        "GitHub에서 `app.py`의 `MY_HOLDINGS` 리스트를 직접 편집 후 커밋하면 "
        "2분 이내 자동 반영됩니다."
    )
    st.markdown("---")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.caption(f"마지막 갱신\n{now}")

# ─────────────────────────────────────────
#  메인 헤더
# ─────────────────────────────────────────
st.title("📊 내 투자 대시보드")
st.caption("데이터 출처: Yahoo Finance · KRX (pykrx) | 국내 종목은 당일 종가 기준")

FX = get_fx_rate()

# ─────────────────────────────────────────
#  섹션 1: 거시 지표
# ─────────────────────────────────────────
st.subheader("🌐 거시 지표 · 주요 지수")
index_data = get_index_data()

# 국내 지수
domestic_labels = ["KOSPI", "KOSDAQ"]
foreign_labels  = ["S&P 500", "나스닥", "다우존스"]
macro_labels    = ["달러 인덱스", "원/달러 환율", "미 10년 국채", "금 선물", "WTI 원유"]

st.markdown("**국내 지수**")
cols = st.columns(2)
for i, label in enumerate(domestic_labels):
    d = index_data.get(label, {})
    price = d.get("price")
    chg   = d.get("chg")
    if price is not None:
        cols[i].metric(label, f"{price:,.2f}", f"{chg:+.2f}%",
                       delta_color="normal" if chg >= 0 else "inverse")
    else:
        cols[i].metric(label, "—", "조회 실패")

st.markdown("**해외 지수**")
cols = st.columns(3)
for i, label in enumerate(foreign_labels):
    d = index_data.get(label, {})
    price = d.get("price")
    chg   = d.get("chg")
    if price is not None:
        cols[i].metric(label, f"{price:,.2f}", f"{chg:+.2f}%",
                       delta_color="normal" if chg >= 0 else "inverse")
    else:
        cols[i].metric(label, "—", "조회 실패")

st.markdown("**거시 지표**")
cols = st.columns(5)
for i, label in enumerate(macro_labels):
    d = index_data.get(label, {})
    price = d.get("price")
    chg   = d.get("chg")
    if price is not None:
        cols[i].metric(label, f"{price:,.2f}", f"{chg:+.2f}%",
                       delta_color="normal" if chg >= 0 else "inverse")
    else:
        cols[i].metric(label, "—", "조회 실패")

st.divider()

# ─────────────────────────────────────────
#  섹션 2: 보유 종목 수익률
# ─────────────────────────────────────────
st.subheader("💼 보유 종목 수익률")

rows = []
for h in MY_HOLDINGS:
    if h["market"] == "KR":
        cur = get_kr_price(h["ticker"])
        avg_krw = h["avg"]
    else:
        cur_usd = get_us_price(h["ticker"])
        cur     = round(cur_usd * FX, 0) if cur_usd else None
        avg_krw = round(h["avg"] * FX, 0)

    if cur is None:
        rows.append({
            "종목명": h["name"], "시장": h["market"],
            "현재가(원)": "조회 실패", "평균단가(원)": f"{avg_krw:,.0f}",
            "수익률(%)": None, "평가손익(원)": None,
            "수량": h["qty"], "평가금액(원)": None,
        })
        continue

    ret = (cur - avg_krw) / avg_krw * 100
    pnl = (cur - avg_krw) * h["qty"]
    val = cur * h["qty"]

    rows.append({
        "종목명":       h["name"],
        "시장":         h["market"],
        "현재가(원)":   f"{cur:,.0f}",
        "평균단가(원)": f"{avg_krw:,.0f}",
        "수익률(%)":    round(ret, 2),
        "평가손익(원)": int(pnl),
        "수량":         h["qty"],
        "평가금액(원)": int(val),
    })

df = pd.DataFrame(rows)

def style_return(val):
    if val is None or not isinstance(val, float):
        return ""
    return "color: #e24b4a; font-weight: 500" if val > 0 else "color: #378add; font-weight: 500"

def style_pnl(val):
    if val is None or not isinstance(val, int):
        return ""
    return "color: #e24b4a; font-weight: 500" if val > 0 else "color: #378add; font-weight: 500"

styled = df.style\
    .applymap(style_return, subset=["수익률(%)"])\
    .applymap(style_pnl,    subset=["평가손익(원)"])

st.dataframe(styled, use_container_width=True, hide_index=True)

# ─────────────────────────────────────────
#  섹션 3: 총계 요약
# ─────────────────────────────────────────
st.subheader("📈 포트폴리오 요약")

valid_rows = [r for r in rows if isinstance(r["평가금액(원)"], int)]
if valid_rows:
    total_val  = sum(r["평가금액(원)"] for r in valid_rows)
    total_cost = sum(
        (h["avg"] if h["market"] == "KR" else round(h["avg"] * FX, 0)) * h["qty"]
        for h in MY_HOLDINGS
        if any(r["종목명"] == h["name"] and isinstance(r["평가금액(원)"], int) for r in rows)
    )
    total_pnl = total_val - total_cost
    total_ret = total_pnl / total_cost * 100 if total_cost else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총 투자금액",  f"{total_cost:,.0f} 원")
    c2.metric("총 평가금액",  f"{total_val:,.0f} 원")
    c3.metric("총 평가손익",  f"{total_pnl:+,.0f} 원",
              delta_color="normal" if total_pnl >= 0 else "inverse")
    c4.metric("총 수익률",    f"{total_ret:+.2f} %",
              delta_color="normal" if total_ret >= 0 else "inverse")
else:
    st.warning("현재가 조회에 실패했습니다. 잠시 후 새로고침 해주세요.")

st.divider()

# ─────────────────────────────────────────
#  섹션 4: 환율 정보
# ─────────────────────────────────────────
st.caption(f"적용 환율: **1 USD = {FX:,.2f} KRW** (실시간 조회) | 해외 종목 평가금액은 이 환율 기준입니다.")

# ─────────────────────────────────────────
#  자동 갱신
# ─────────────────────────────────────────
if auto_refresh:
    time.sleep(300)
    st.rerun()
