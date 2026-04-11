import streamlit as st
import yfinance as yf
from pykrx import stock
import pandas as pd
from datetime import datetime, timedelta
import time

# ══════════════════════════════════════════════════
#  페이지 설정
# ══════════════════════════════════════════════════
st.set_page_config(
    page_title="내 투자 대시보드",
    page_icon="📈",
    layout="wide",
)

# ══════════════════════════════════════════════════
#  보유 종목 목록
#  수정 방법: GitHub에서 이 파일 편집 → Commit changes
#             약 2분 후 Render에 자동 반영
#  market: "KR" = 국내,  "US" = 해외(달러)
# ══════════════════════════════════════════════════
MY_HOLDINGS = [
    {"ticker": "005930", "name": "삼성전자",    "qty": 20,  "avg": 72000,  "market": "KR"},
    {"ticker": "035720", "name": "카카오",      "qty": 10,  "avg": 58000,  "market": "KR"},
    {"ticker": "000660", "name": "SK하이닉스",  "qty":  5,  "avg": 130000, "market": "KR"},
    {"ticker": "AAPL",   "name": "Apple",       "qty":  5,  "avg": 172.0,  "market": "US"},
    {"ticker": "SCHD",   "name": "SCHD ETF",    "qty": 10,  "avg": 77.0,   "market": "US"},
]

# ══════════════════════════════════════════════════
#  날짜 헬퍼
# ══════════════════════════════════════════════════
def _today() -> str:
    return datetime.today().strftime("%Y%m%d")

def _date_back(days: int) -> str:
    return (datetime.today() - timedelta(days=days)).strftime("%Y%m%d")

# ══════════════════════════════════════════════════
#  국내 종목 현재가 — pykrx
# ══════════════════════════════════════════════════
@st.cache_data(ttl=300)
def get_kr_price(ticker: str) -> int | None:
    for days_back in range(0, 8):
        date = _date_back(days_back)
        try:
            df = stock.get_market_ohlcv(date, date, ticker)
            if df is not None and not df.empty:
                close = int(df["종가"].iloc[-1])
                if close > 0:
                    return close
        except Exception:
            continue
    return None

# ══════════════════════════════════════════════════
#  국내 종목 세부 지표 — pykrx
# ══════════════════════════════════════════════════
@st.cache_data(ttl=300)
def get_kr_fundamental(ticker: str) -> dict:
    for days_back in range(0, 8):
        date = _date_back(days_back)
        try:
            df = stock.get_market_fundamental(date, date, ticker)
            if df is not None and not df.empty:
                row = df.iloc[-1]
                return {
                    "PER": round(float(row.get("PER", 0)), 2),
                    "PBR": round(float(row.get("PBR", 0)), 2),
                    "DIV": round(float(row.get("DIV", 0)), 2),
                }
        except Exception:
            continue
    return {"PER": None, "PBR": None, "DIV": None}

# ══════════════════════════════════════════════════
#  국내 지수 — pykrx
# ══════════════════════════════════════════════════
@st.cache_data(ttl=300)
def get_kr_index(index_code: str, label: str) -> dict:
    start = _date_back(10)
    end   = _today()
    try:
        df = stock.get_index_ohlcv(start, end, index_code)
        if df is not None and len(df) >= 2:
            cur  = float(df["종가"].iloc[-1])
            prev = float(df["종가"].iloc[-2])
            return {"label": label, "price": round(cur, 2),
                    "chg": round((cur - prev) / prev * 100, 2)}
    except Exception:
        pass
    return {"label": label, "price": None, "chg": None}

# ══════════════════════════════════════════════════
#  해외 종목 현재가 — yfinance
# ══════════════════════════════════════════════════
@st.cache_data(ttl=300)
def get_us_price(ticker: str) -> float | None:
    try:
        return round(yf.Ticker(ticker).fast_info.last_price, 2)
    except Exception:
        return None

# ══════════════════════════════════════════════════
#  해외 지수·거시 지표 — yfinance
# ══════════════════════════════════════════════════
@st.cache_data(ttl=300)
def get_yf_data(ticker: str, label: str) -> dict:
    try:
        info  = yf.Ticker(ticker).fast_info
        price = info.last_price
        prev  = info.previous_close
        chg   = (price - prev) / prev * 100
        return {"label": label, "price": round(price, 2), "chg": round(chg, 2)}
    except Exception:
        return {"label": label, "price": None, "chg": None}

# ══════════════════════════════════════════════════
#  공통 렌더링 헬퍼
# ══════════════════════════════════════════════════
def show_metric(col, d: dict):
    if d["price"] is not None:
        col.metric(
            d["label"],
            f"{d['price']:,.2f}",
            f"{d['chg']:+.2f}%",
            delta_color="normal" if d["chg"] >= 0 else "inverse",
        )
    else:
        col.metric(d["label"], "—", "조회 실패")

# ══════════════════════════════════════════════════
#  사이드바
# ══════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### ⚙️ 설정")
    auto_refresh = st.toggle("5분 자동 갱신", value=True)
    st.divider()
    st.markdown("**종목 수정 방법**")
    st.caption(
        "GitHub → `app.py` → ✏️ 편집\n\n"
        "`MY_HOLDINGS` 수정 후\n\n"
        "**Commit changes** 클릭\n\n"
        "→ 약 2분 후 자동 반영"
    )
    st.divider()
    st.caption(f"갱신 시각\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ══════════════════════════════════════════════════
#  헤더
# ══════════════════════════════════════════════════
st.title("📊 내 투자 대시보드")
st.caption(
    "국내 데이터: KRX (pykrx)  |  해외 데이터: Yahoo Finance (yfinance)  |  "
    "국내 종목 — 당일 종가 기준  |  해외 종목 — 실시간 (15분 지연)"
)

fx_data = get_yf_data("USDKRW=X", "원/달러 환율")
FX = fx_data["price"] if fx_data["price"] else 1330.0

# ══════════════════════════════════════════════════
#  섹션 1 — 국내 지수
# ══════════════════════════════════════════════════
st.subheader("🇰🇷 국내 지수")
domestic = [
    get_kr_index("1001", "KOSPI"),
    get_kr_index("2001", "KOSDAQ"),
    get_kr_index("1028", "KOSPI 200"),
]
cols = st.columns(3)
for col, d in zip(cols, domestic):
    show_metric(col, d)

# ══════════════════════════════════════════════════
#  섹션 2 — 해외 지수
# ══════════════════════════════════════════════════
st.subheader("🌎 해외 지수")
foreign = [
    get_yf_data("^GSPC", "S&P 500"),
    get_yf_data("^IXIC", "나스닥"),
    get_yf_data("^DJI",  "다우존스"),
]
cols = st.columns(3)
for col, d in zip(cols, foreign):
    show_metric(col, d)

# ══════════════════════════════════════════════════
#  섹션 3 — 거시 지표
# ══════════════════════════════════════════════════
st.subheader("📡 거시 지표")
macro = [
    get_yf_data("DX-Y.NYB", "달러 인덱스"),
    fx_data,
    get_yf_data("^TNX",     "미 10년 국채"),
    get_yf_data("GC=F",     "금 선물"),
    get_yf_data("CL=F",     "WTI 원유"),
]
cols = st.columns(5)
for col, d in zip(cols, macro):
    show_metric(col, d)

st.divider()

# ══════════════════════════════════════════════════
#  섹션 4 — 보유 종목 수익률
# ══════════════════════════════════════════════════
st.subheader("💼 보유 종목 수익률")

rows = []
for h in MY_HOLDINGS:
    if h["market"] == "KR":
        cur_krw  = get_kr_price(h["ticker"])
        avg_krw  = h["avg"]
        cur_disp = f"{cur_krw:,}원" if cur_krw else "조회 실패"
        fund     = get_kr_fundamental(h["ticker"])
    else:
        cur_usd  = get_us_price(h["ticker"])
        cur_krw  = round(cur_usd * FX) if cur_usd else None
        avg_krw  = round(h["avg"] * FX)
        cur_disp = f"${cur_usd:.2f}" if cur_usd else "조회 실패"
        fund     = {"PER": None, "PBR": None, "DIV": None}

    if cur_krw:
        ret = (cur_krw - avg_krw) / avg_krw * 100
        pnl = (cur_krw - avg_krw) * h["qty"]
        val =  cur_krw * h["qty"]
        rows.append({
            "종목명":        h["name"],
            "시장":          h["market"],
            "현재가":        cur_disp,
            "평균단가(원)":  f"{avg_krw:,}",
            "수익률(%)":     round(ret, 2),
            "평가손익(원)":  int(pnl),
            "수량":          h["qty"],
            "평가금액(원)":  int(val),
            "PER":           fund["PER"],
            "PBR":           fund["PBR"],
            "배당수익률(%)": fund["DIV"],
        })
    else:
        rows.append({
            "종목명": h["name"],      "시장": h["market"],
            "현재가": cur_disp,       "평균단가(원)": f"{avg_krw:,}",
            "수익률(%)": None,        "평가손익(원)": None,
            "수량": h["qty"],         "평가금액(원)": None,
            "PER": None,              "PBR": None,
            "배당수익률(%)": None,
        })

df = pd.DataFrame(rows)

def _color_ret(v):
    if not isinstance(v, float): return ""
    return "color:#e24b4a;font-weight:500" if v > 0 else "color:#378add;font-weight:500"

def _color_pnl(v):
    if not isinstance(v, int): return ""
    return "color:#e24b4a;font-weight:500" if v > 0 else "color:#378add;font-weight:500"

st.dataframe(
    df.style
      .applymap(_color_ret, subset=["수익률(%)"])
      .applymap(_color_pnl, subset=["평가손익(원)"]),
    use_container_width=True,
    hide_index=True,
)

# ══════════════════════════════════════════════════
#  섹션 5 — 포트폴리오 요약
# ══════════════════════════════════════════════════
st.subheader("📈 포트폴리오 요약")

valid = [r for r in rows if r["평가금액(원)"] is not None]
if valid:
    total_val  = sum(r["평가금액(원)"] for r in valid)
    total_cost = sum(
        (h["avg"] if h["market"] == "KR" else round(h["avg"] * FX)) * h["qty"]
        for h in MY_HOLDINGS
        if any(r["종목명"] == h["name"] and r["평가금액(원)"] is not None
               for r in rows)
    )
    total_pnl = total_val - total_cost
    total_ret = total_pnl / total_cost * 100 if total_cost else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총 투자금액", f"{total_cost:,.0f}원")
    c2.metric("총 평가금액", f"{total_val:,.0f}원")
    c3.metric("총 평가손익", f"{total_pnl:+,.0f}원",
              delta_color="normal" if total_pnl >= 0 else "inverse")
    c4.metric("총 수익률",   f"{total_ret:+.2f}%",
              delta_color="normal" if total_ret >= 0 else "inverse")
else:
    st.warning("현재가 조회에 실패했습니다. 잠시 후 새로고침 해주세요.")

st.caption(
    f"적용 환율: 1 USD = {FX:,.2f} KRW (실시간)  |  "
    "해외 종목 평가금액은 이 환율로 환산한 값입니다."
)

# ══════════════════════════════════════════════════
#  자동 갱신
# ══════════════════════════════════════════════════
if auto_refresh:
    time.sleep(300)
    st.rerun()
