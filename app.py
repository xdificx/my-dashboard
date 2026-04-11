import streamlit as st
import pandas as pd
import time
from datetime import datetime
from services.data_service import get_ticker_data, get_history
from services.db_service import get_all_holdings, add_holding, update_holding, delete_holding
from services.calculations import calculate_portfolio_row
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ══════════════════════════════════════════════════
#  페이지 설정
# ══════════════════════════════════════════════════
st.set_page_config(
    page_title="Main Dashboard",
    layout="wide",
)

# ══════════════════════════════════════════════════
#  증권사 앱 스타일 카드
# ══════════════════════════════════════════════════
def show_card(d: dict):
    if not d.get("ok"):
        st.markdown(f"""
<div style="padding:10px 4px 14px 4px;border-bottom:1px solid #e0e0e0;">
  <div style="font-size:12px;color:#888;">{d.get("label","")}</div>
  <div style="font-size:22px;font-weight:700;color:#aaa;">—</div>
  <div style="font-size:12px;color:#aaa;">조회 실패</div>
</div>""", unsafe_allow_html=True)
        return
    up    = d["chg"] >= 0
    color = "#e24b4a" if up else "#378add"
    arrow = "▲" if up else "▼"
    prev  = d.get("prev", d["price"])
    diff  = abs(d["price"] - prev)
    chg_a = abs(d["chg"])
    st.markdown(f"""
<div style="padding:10px 4px 14px 4px;border-bottom:1px solid #e0e0e0;">
  <div style="font-size:12px;color:#888;margin-bottom:2px;">{d.get("label","")}</div>
  <div style="font-size:22px;font-weight:700;margin-bottom:4px;">{d["price"]:,.2f}</div>
  <div style="display:flex;align-items:center;gap:8px;">
    <span style="font-size:13px;font-weight:600;color:{color};">{arrow} {diff:,.2f}</span>
    <span style="background:{color};color:#fff;font-size:12px;font-weight:700;
                 padding:2px 8px;border-radius:4px;">{chg_a:.2f}%</span>
  </div>
</div>""", unsafe_allow_html=True)


def fetch(ticker, label):
    d = get_ticker_data(ticker)
    d["label"] = label
    return d

# ══════════════════════════════════════════════════
#  사이드바
# ══════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### ⚙️ Setting")
    auto_refresh = st.toggle("5분 자동 갱신", value=True)
    st.divider()
    st.markdown("### ➕ 종목 추가")
    with st.form("add_form", clear_on_submit=True):
        f_ticker = st.text_input("티커", placeholder="005930.KS")
        f_name   = st.text_input("종목명", placeholder="삼성전자")
        f_qty    = st.number_input("수량", min_value=1, value=1)
        f_avg    = st.number_input("평균단가", min_value=0.0, value=0.0, format="%.2f")
        f_market = st.selectbox("시장", ["KR", "US"])
        if st.form_submit_button("추가") and f_ticker and f_name:
            add_holding({"ticker": f_ticker, "name": f_name,
                         "qty": f_qty, "avg": f_avg, "market": f_market})
            st.success(f"{f_name} 추가됨")
            st.rerun()
    st.divider()
    st.caption(f"갱신 시각\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ══════════════════════════════════════════════════
#  헤더
# ══════════════════════════════════════════════════
st.markdown("""
<div style="padding:8px 0 4px 0;">
  <span style="font-size:28px;font-weight:800;">📊 Main Dashboard</span>
</div>
<div style="font-size:12px;color:#888;margin-bottom:8px;">
  데이터: Yahoo Finance (yfinance) | 15분 지연 |
  갱신 시각: {now}
</div>
""".format(now=__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
unsafe_allow_html=True)

fx = fetch("USDKRW=X", "원/달러 환율")
FX = fx["price"] if fx.get("ok") else 1330.0

# ══════════════════════════════════════════════════
#  섹션 1 — Market Indicator (3열 나란히, 항목 세로)
# ══════════════════════════════════════════════════
st.markdown("### 📈 Market Indicator")

# 열 간격을 줄이기 위해 gap 옵션 사용
col_kr, col_us, col_macro = st.columns([1, 1, 1], gap="small")

with col_kr:
    st.markdown(
        '<div style="background:#fff5f5;border-radius:12px;padding:14px 16px 6px 16px;">'
        '<div style="font-size:13px;font-weight:700;color:#e24b4a;margin-bottom:8px;">'
        '🇰🇷 국내 지수</div>',
        unsafe_allow_html=True
    )
    for t, n in [("^KS11","KOSPI"),("^KQ11","KOSDAQ"),("^KS200","KOSPI 200")]:
        show_card(fetch(t, n))
    st.markdown('</div>', unsafe_allow_html=True)

with col_us:
    st.markdown(
        '<div style="background:#f5f8ff;border-radius:12px;padding:14px 16px 6px 16px;">'
        '<div style="font-size:13px;font-weight:700;color:#378add;margin-bottom:8px;">'
        '🌎 해외 지수</div>',
        unsafe_allow_html=True
    )
    for t, n in [("^GSPC","S&P 500"),("^IXIC","나스닥"),("^DJI","다우존스")]:
        show_card(fetch(t, n))
    st.markdown('</div>', unsafe_allow_html=True)

with col_macro:
    st.markdown(
        '<div style="background:#f5f5f5;border-radius:12px;padding:14px 16px 6px 16px;">'
        '<div style="font-size:13px;font-weight:700;color:#555;margin-bottom:8px;">'
        '📡 거시 지표</div>',
        unsafe_allow_html=True
    )
    for t, n in [("USDKRW=X","원/달러 환율"),("^TNX","미 10년 국채"),("^VIX","변동성 (VIX)")]:
        show_card(fetch(t, n))
    st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# ══════════════════════════════════════════════════
#  섹션 2 — 보유 종목 수익률
# ══════════════════════════════════════════════════
st.subheader("💼 보유 종목 수익률")
holdings = get_all_holdings()

if not holdings:
    st.info("왼쪽 사이드바에서 종목을 추가해주세요.")
else:
    rows = []
    for h in holdings:
        d = get_ticker_data(h["ticker"])
        if d.get("ok"):
            rows.append(calculate_portfolio_row(h, d["price"], FX))
        else:
            rows.append({
                "종목": h["name"], "현재가": "조회 실패",
                "수량": h["qty"], "평가금액(원)": "-",
                "평가손익(원)": "-", "수익률(%)": None,
            })

    df = pd.DataFrame(rows)

    def _style(v):
        if not isinstance(v, (int, float)): return ""
        return "color:#e24b4a;font-weight:600" if v > 0 else "color:#378add;font-weight:600"

    st.dataframe(
        df.style.map(_style, subset=["수익률(%)"]),
        use_container_width=True, hide_index=True,
    )

    # 포트폴리오 요약
    try:
        total_val  = sum(
            int(str(r["평가금액(원)"]).replace(",",""))
            for r in rows if r["평가금액(원)"] != "-"
        )
        total_cost = sum(
            (round(h["avg"] * FX) if h["market"] == "US" else round(h["avg"])) * h["qty"]
            for h in holdings
        )
        total_pnl = total_val - total_cost
        total_ret = total_pnl / total_cost * 100 if total_cost else 0
        st.markdown("---")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("총 투자금액", f"{total_cost:,.0f}원")
        c2.metric("총 평가금액", f"{total_val:,.0f}원")
        c3.metric("총 평가손익", f"{total_pnl:+,.0f}원",
                  delta_color="normal" if total_pnl >= 0 else "inverse")
        c4.metric("총 수익률", f"{total_ret:+.2f}%",
                  delta_color="normal" if total_ret >= 0 else "inverse")
    except Exception:
        pass

    st.caption(f"적용 환율: 1 USD = {FX:,.2f} KRW")

st.divider()

# ══════════════════════════════════════════════════
#  섹션 3 — 종목 차트
# ══════════════════════════════════════════════════
st.subheader("📈 종목 차트")
holdings = get_all_holdings()

if holdings:
    selected = st.selectbox("종목 선택", [h["name"] for h in holdings])
    ticker   = next(h["ticker"] for h in holdings if h["name"] == selected)
    period   = st.radio("기간", ["1mo","3mo","6mo","1y","2y"], horizontal=True, index=3)
    hist     = get_history(ticker, period=period)

    if not hist.empty:
        if isinstance(hist.columns, pd.MultiIndex):
            hist.columns = hist.columns.get_level_values(0)
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                            row_heights=[0.75, 0.25], vertical_spacing=0.03)
        fig.add_trace(go.Candlestick(
            x=hist.index, open=hist["Open"], high=hist["High"],
            low=hist["Low"], close=hist["Close"],
            increasing_line_color="#e24b4a",
            decreasing_line_color="#378add", name="가격",
        ), row=1, col=1)
        fig.add_trace(go.Bar(
            x=hist.index, y=hist["Volume"],
            marker_color="#aaaaaa", name="거래량",
        ), row=2, col=1)
        fig.update_layout(xaxis_rangeslider_visible=False, height=500,
                          margin=dict(t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("차트 데이터를 불러오지 못했습니다.")
else:
    st.info("종목을 추가하면 차트를 볼 수 있습니다.")

st.divider()

# ══════════════════════════════════════════════════
#  섹션 4 — 종목 관리 (수정 / 삭제)
# ══════════════════════════════════════════════════
st.subheader("⚙️ 종목 관리")
holdings = get_all_holdings()

if holdings:
    for i, h in enumerate(holdings):
        with st.expander(f"{h['name']} ({h['ticker']})"):
            c1, c2, c3 = st.columns([2, 2, 1])
            new_qty = c1.number_input("수량", value=h["qty"], key=f"qty_{i}")
            new_avg = c2.number_input("평균단가", value=float(h["avg"]),
                                      key=f"avg_{i}", format="%.2f")
            c3.markdown("<br>", unsafe_allow_html=True)
            if c3.button("수정", key=f"upd_{i}"):
                update_holding(h["id"], new_qty, new_avg)
                st.success("수정됨")
                st.rerun()
            if st.button("🗑️ 삭제", key=f"del_{i}", type="secondary"):
                delete_holding(h["id"])
                st.rerun()
else:
    st.info("등록된 종목이 없습니다.")

# ══════════════════════════════════════════════════
#  자동 갱신
# ══════════════════════════════════════════════════
if auto_refresh:
    time.sleep(300)
    st.rerun()
