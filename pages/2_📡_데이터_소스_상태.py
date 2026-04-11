import streamlit as st
import yfinance as yf
from pykrx import stock
from datetime import datetime, timedelta
import traceback
import time

st.set_page_config(
    page_title="데이터 소스 상태",
    page_icon="📡",
    layout="wide",
)

# ══════════════════════════════════════════════════
#  날짜 헬퍼
# ══════════════════════════════════════════════════
def _today() -> str:
    return datetime.today().strftime("%Y%m%d")

def _date_back(days: int) -> str:
    return (datetime.today() - timedelta(days=days)).strftime("%Y%m%d")

# ══════════════════════════════════════════════════
#  점검 대상 목록
# ══════════════════════════════════════════════════

# pykrx 점검 항목
PYKRX_CHECKS = [
    {"label": "KOSPI",      "type": "index",  "code": "1001"},
    {"label": "KOSDAQ",     "type": "index",  "code": "2001"},
    {"label": "KOSPI 200",  "type": "index",  "code": "1028"},
    {"label": "삼성전자",   "type": "stock",  "code": "005930"},
]

# yfinance 점검 항목
YFINANCE_CHECKS = [
    {"label": "S&P 500",      "ticker": "^GSPC"},
    {"label": "나스닥",        "ticker": "^IXIC"},
    {"label": "다우존스",      "ticker": "^DJI"},
    {"label": "달러 인덱스",   "ticker": "DX-Y.NYB"},
    {"label": "원/달러 환율",  "ticker": "USDKRW=X"},
    {"label": "미 10년 국채",  "ticker": "^TNX"},
    {"label": "금 선물",       "ticker": "GC=F"},
    {"label": "WTI 원유",      "ticker": "CL=F"},
]

# ══════════════════════════════════════════════════
#  개별 점검 함수
# ══════════════════════════════════════════════════
@st.cache_data(ttl=300)
def check_pykrx_index(code: str) -> tuple[bool, str, str]:
    """(성공여부, 값, 오류메시지)"""
    try:
        start = _date_back(10)
        end   = _today()
        df = stock.get_index_ohlcv(start, end, code)
        if df is not None and not df.empty:
            val = float(df["종가"].iloc[-1])
            return True, f"{val:,.2f}", ""
        return False, "", f"빈 데이터 반환 (start={start}, end={end})"
    except Exception:
        lines = [l.strip() for l in traceback.format_exc().strip().splitlines() if l.strip()]
        return False, "", " | ".join(lines[-2:])[:300]

@st.cache_data(ttl=300)
def check_pykrx_stock(code: str) -> tuple[bool, str, str]:
    try:
        for days_back in range(0, 8):
            date = _date_back(days_back)
            df = stock.get_market_ohlcv(date, date, code)
            if df is not None and not df.empty:
                val = int(df["종가"].iloc[-1])
                if val > 0:
                    return True, f"{val:,}원", ""
        return False, "", "8일치 탐색 후에도 데이터 없음"
    except Exception:
        lines = [l.strip() for l in traceback.format_exc().strip().splitlines() if l.strip()]
        return False, "", " | ".join(lines[-2:])[:300]

@st.cache_data(ttl=300)
def check_yfinance_ticker(ticker: str) -> tuple[bool, str, str]:
    try:
        info  = yf.Ticker(ticker).fast_info
        price = info.last_price
        if price and price > 0:
            return True, f"{price:,.4f}", ""
        return False, "", "가격 0 또는 None 반환"
    except Exception:
        lines = [l.strip() for l in traceback.format_exc().strip().splitlines() if l.strip()]
        return False, "", " | ".join(lines[-2:])[:300]

# ══════════════════════════════════════════════════
#  사이드바
# ══════════════════════════════════════════════════
with st.sidebar:
    st.divider()
    auto_refresh = st.toggle("5분 자동 갱신", value=False)
    if st.button("🔄 지금 즉시 재점검"):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.caption(f"점검 시각\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ══════════════════════════════════════════════════
#  헤더
# ══════════════════════════════════════════════════
st.title("📡 데이터 소스 상태")
st.caption("pykrx (KRX) 와 yfinance (Yahoo Finance) 의 연결 상태를 항목별로 점검합니다.")

# ══════════════════════════════════════════════════
#  pykrx 섹션
# ══════════════════════════════════════════════════
st.subheader("🇰🇷 pykrx — KRX 데이터")

pykrx_results = []
for item in PYKRX_CHECKS:
    if item["type"] == "index":
        ok, val, err = check_pykrx_index(item["code"])
    else:
        ok, val, err = check_pykrx_stock(item["code"])
    pykrx_results.append({"item": item, "ok": ok, "val": val, "err": err})

# 전체 요약
pykrx_fail = [r for r in pykrx_results if not r["ok"]]
if not pykrx_fail:
    st.success(f"✅ pykrx 전체 정상 — {len(pykrx_results)}개 항목 모두 연결 성공")
else:
    st.error(f"❌ pykrx 연결 실패 — {len(pykrx_fail)}개 항목 실패 / {len(pykrx_results)}개 중")

# 항목별 상세
cols = st.columns(len(PYKRX_CHECKS))
for col, r in zip(cols, pykrx_results):
    with col:
        if r["ok"]:
            st.success(f"**{r['item']['label']}**\n\n{r['val']}")
        else:
            st.error(f"**{r['item']['label']}**\n\n연결 실패")
            with st.expander("오류 상세"):
                st.code(r["err"] or "오류 메시지 없음", language=None)

st.divider()

# ══════════════════════════════════════════════════
#  yfinance 섹션
# ══════════════════════════════════════════════════
st.subheader("🌎 yfinance — Yahoo Finance 데이터")

yf_results = []
for item in YFINANCE_CHECKS:
    ok, val, err = check_yfinance_ticker(item["ticker"])
    yf_results.append({"item": item, "ok": ok, "val": val, "err": err})

# 전체 요약
yf_fail = [r for r in yf_results if not r["ok"]]
if not yf_fail:
    st.success(f"✅ yfinance 전체 정상 — {len(yf_results)}개 항목 모두 연결 성공")
else:
    st.error(f"❌ yfinance 연결 실패 — {len(yf_fail)}개 항목 실패 / {len(yf_results)}개 중")

# 항목별 상세 — 4열 그리드
n = len(YFINANCE_CHECKS)
cols = st.columns(4)
for i, r in enumerate(yf_results):
    with cols[i % 4]:
        if r["ok"]:
            st.success(f"**{r['item']['label']}**\n\n{r['val']}")
        else:
            st.error(f"**{r['item']['label']}**\n\n연결 실패")
            with st.expander("오류 상세"):
                st.code(r["err"] or "오류 메시지 없음", language=None)

st.divider()

# ══════════════════════════════════════════════════
#  전체 종합 요약
# ══════════════════════════════════════════════════
st.subheader("📋 전체 종합")

total_checks = len(pykrx_results) + len(yf_results)
total_fail   = len(pykrx_fail) + len(yf_fail)
total_ok     = total_checks - total_fail

if total_fail == 0:
    st.success(f"🟢 모든 데이터 소스 정상 — {total_ok}/{total_checks} 항목 연결 성공")
elif total_fail < total_checks:
    st.warning(f"🟡 일부 연결 실패 — {total_ok}/{total_checks} 항목 연결 성공")
    st.markdown("**실패 항목 목록:**")
    for r in pykrx_fail + yf_fail:
        st.markdown(f"- ❌ {r['item']['label']}: `{r['err'][:80] if r['err'] else '오류 메시지 없음'}`")
else:
    st.error(f"🔴 전체 연결 불가 — {total_fail}개 항목 모두 실패")

# ══════════════════════════════════════════════════
#  자동 갱신
# ══════════════════════════════════════════════════
if auto_refresh:
    time.sleep(300)
    st.rerun()
