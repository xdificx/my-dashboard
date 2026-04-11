import streamlit as st
import yfinance as yf
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
#
#  market: "KR" = 국내,  "US" = 해외(달러)
#  KR 티커: 6자리 종목코드 + ".KS" (코스피) 또는 ".KQ" (코스닥)
#  예) 삼성전자=005930.KS, 카카오=035720.KQ
# ══════════════════════════════════════════════════
MY_HOLDINGS = [
    {"ticker": "005930.KS", "name": "삼성전자",    "qty": 20,  "avg": 72000,  "market": "KR"},
    {"ticker": "035720.KQ", "name": "카카오",      "qty": 10,  "avg": 58000,  "market": "KR"},
    {"ticker": "000660.KS", "name": "SK하이닉스",  "qty":  5,  "avg": 130000, "market": "KR"},
    {"ticker": "AAPL",      "name": "Apple",       "qty":  5,  "avg": 172.0,  "market": "US"},
    {"ticker": "SCHD",      "name": "SCHD ETF",    "qty": 10,  "avg": 77.0,   "market": "US"},
]

# ══════════════════════════════════════════════════
#  공통 데이터 조회 — yfinance
# ══════════════════════════════════════════════════
@st.cache_data(ttl=300)
def get_ticker_data(ticker: str, label: str) -> dict:
    """지수·종목·거시지표 범용 조회"""
    try:
        info  = yf.Ticker(ticker).fast_info
        price = info.last_price
        prev  = info.previous_close
        if price and price > 0 and prev and prev > 0:
            chg  = (price - prev) / prev * 100
            diff = price - prev          # 포인트 등락
            return {
                "label": label,
                "price": round(price, 2),
                "chg":   round(chg, 2),
                "diff":  round(diff, 2),  # 전일 대비 포인트
                "ok":    True,
            }
    except Exception:
        pass
    return {"label": label, "price": None, "chg": None, "diff": None, "ok": False}

# ══════════════════════════════════════════════════
#  공통 렌더링 헬퍼
# ══════════════════════════════════════════════════
def show_metric(container, d: dict):
    """증권사 앱 스타일 카드: ▲빨강 / ▼파랑, 퍼센트 배경 박스"""
    if d["ok"]:
        up     = d["chg"] >= 0
        color  = "#e24b4a" if up else "#378add"
        arrow  = "▲" if up else "▼"
        diff_abs = abs(d["diff"])
        chg_abs  = abs(d["chg"])
        html = f"""
<div style="padding:10px 4px 14px 4px; border-bottom:1px solid #e0e0e0;">
  <div style="font-size:12px; color:#888; margin-bottom:2px;">{d["label"]}</div>
  <div style="font-size:22px; font-weight:700; color:var(--text-color,#111); margin-bottom:4px;">
    {d["price"]:,.2f}
  </div>
  <div style="display:flex; align-items:center; gap:8px;">
    <span style="font-size:13px; font-weight:600; color:{color};">
      {arrow} {diff_abs:,.2f}
    </span>
    <span style="background:{color}; color:#fff; font-size:12px;
                 font-weight:700; padding:2px 8px; border-radius:4px;">
      {chg_abs:.2f}%
    </span>
  </div>
</div>"""
        container.markdown(html, unsafe_allow_html=True)
    else:
        container.markdown(
            f"""<div style="padding:10px 4px 14px 4px; border-bottom:1px solid #e0e0e0;">
  <div style="font-size:12px; color:#888;">{d["label"]}</div>
  <div style="font-size:22px; font-weight:700; color:#aaa;">—</div>
  <div style="font-size:12px; color:#aaa;">조회 실패</div>
</div>""",
            unsafe_allow_html=True,
        )

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
    "데이터: Yahoo Finance (yfinance)  |  "
    "국내 종목 — 당일 종가 기준 (15분 지연)  |  "
    "해외 종목 — 실시간 (15분 지연)"
)

# 환율 — 이후 섹션에서 재사용
fx_data = get_ticker_data("USDKRW=X", "원/달러 환율")
FX = fx_data["price"] if fx_data["ok"] else 1330.0

# ══════════════════════════════════════════════════
#  섹션 1·2·3 — 국내 지수 / 해외 지수 / 거시 지표
#  3개 그룹을 가로 3열로 나란히, 각 항목은 세로 배치
# ══════════════════════════════════════════════════
domestic = [
    get_ticker_data("^KS11",  "KOSPI"),
    get_ticker_data("^KQ11",  "KOSDAQ"),
    get_ticker_data("^KS200", "KOSPI 200"),
]
foreign = [
    get_ticker_data("^GSPC", "S&P 500"),
    get_ticker_data("^IXIC", "나스닥"),
    get_ticker_data("^DJI",  "다우존스"),
]
macro = [
    fx_data,
    get_ticker_data("^TNX", "미 10년 국채"),
    get_ticker_data("^VIX", "변동성 (VIX)"),
]

col_kr, col_us, col_macro = st.columns(3)

with col_kr:
    st.markdown("**🇰🇷 국내 지수**")
    for d in domestic:
        show_metric(st, d)

with col_us:
    st.markdown("**🌎 해외 지수**")
    for d in foreign:
        show_metric(st, d)

with col_macro:
    st.markdown("**📡 거시 지표**")
    for d in macro:
        show_metric(st, d)

st.divider()

# ══════════════════════════════════════════════════
#  섹션 4 — 보유 종목 수익률
# ══════════════════════════════════════════════════
st.subheader("💼 보유 종목 수익률")

rows = []
for h in MY_HOLDINGS:
    d = get_ticker_data(h["ticker"], h["name"])

    if h["market"] == "KR":
        cur_krw  = round(d["price"]) if d["ok"] else None
        avg_krw  = h["avg"]
        cur_disp = f"{cur_krw:,}원" if cur_krw else "조회 실패"
    else:
        cur_usd  = d["price"] if d["ok"] else None
        cur_krw  = round(cur_usd * FX) if cur_usd else None
        avg_krw  = round(h["avg"] * FX)
        cur_disp = f"${cur_usd:.2f}" if cur_usd else "조회 실패"

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
        })
    else:
        rows.append({
            "종목명": h["name"],      "시장": h["market"],
            "현재가": cur_disp,       "평균단가(원)": f"{avg_krw:,}",
            "수익률(%)": None,        "평가손익(원)": None,
            "수량": h["qty"],         "평가금액(원)": None,
        })

df = pd.DataFrame(rows)

def _color_ret(v):
    if not isinstance(v, float): return ""
    # 상승=빨강, 하락=파랑 (증권사 앱 기준)
    return "color:#e24b4a;font-weight:600" if v > 0 else "color:#378add;font-weight:600"

def _color_pnl(v):
    if not isinstance(v, int): return ""
    return "color:#e24b4a;font-weight:600" if v > 0 else "color:#378add;font-weight:600"

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
