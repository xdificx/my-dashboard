import streamlit as st
import pandas as pd
from datetime import datetime
from services.data_service import get_ticker_data
from services.db_service import get_all_holdings, add_holding, update_holding, delete_holding
from services.calculations import calculate_portfolio_row

st.set_page_config(
    page_title="Portfolio",
    page_icon="💼",
    layout="wide",
)

with st.sidebar:
    st.markdown("### ⚙️ 설정")
    st.caption(f"갱신 시각\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ══════════════════════════════════════════════════
#  헤더 + 종목 추가 버튼 (우측 상단)
# ══════════════════════════════════════════════════
hdr_col, btn_col = st.columns([4, 1])

with hdr_col:
    st.markdown("""
<div style="padding:8px 0 4px 0;">
  <span style="font-size:28px;font-weight:800;">💼 Portfolio</span>
</div>
<div style="font-size:12px;color:#888;margin-bottom:8px;">
  데이터: Yahoo Finance (yfinance) | 15분 지연
</div>
""", unsafe_allow_html=True)

with btn_col:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("➕ 종목 추가", use_container_width=True):
        st.session_state["show_add_form"] = not st.session_state.get("show_add_form", False)

# 종목 추가 폼 (토글)
if st.session_state.get("show_add_form", False):
    with st.container(border=True):
        st.markdown("**➕ 종목 추가**")
        c1, c2, c3, c4, c5, c6 = st.columns([2, 2, 1, 2, 1, 1])
        f_ticker = c1.text_input("티커", placeholder="005930.KS", key="f_ticker")
        f_name   = c2.text_input("종목명", placeholder="삼성전자", key="f_name")
        f_qty    = c3.number_input("수량", min_value=1, value=1, key="f_qty")
        f_avg    = c4.number_input("평균단가", min_value=0.0, value=0.0,
                                   format="%.2f", key="f_avg")
        f_market = c5.selectbox("시장", ["KR", "US"], key="f_market")
        c6.markdown("<br>", unsafe_allow_html=True)
        if c6.button("추가", key="add_btn", use_container_width=True):
            if f_ticker and f_name:
                add_holding({"ticker": f_ticker, "name": f_name,
                             "qty": f_qty, "avg": f_avg, "market": f_market})
                st.success(f"{f_name} 추가됨")
                st.session_state["show_add_form"] = False
                st.rerun()
            else:
                st.warning("티커와 종목명을 입력해주세요.")

# 환율
fx = get_ticker_data("USDKRW=X")
FX = fx["price"] if fx.get("ok") else 1330.0

holdings = get_all_holdings()

# ══════════════════════════════════════════════════
#  섹션 1 — 보유 종목 수익률 테이블
# ══════════════════════════════════════════════════
st.markdown("### 📊 보유 종목 수익률")

if not holdings:
    st.info("우측 상단 '➕ 종목 추가' 버튼으로 종목을 추가해주세요.")
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
    st.caption(f"적용 환율: 1 USD = {FX:,.2f} KRW")

st.divider()

# ══════════════════════════════════════════════════
#  섹션 2 — 종목 관리 (수정 / 삭제)
# ══════════════════════════════════════════════════
st.markdown("### ⚙️ 종목 관리")

if holdings:
    for i, h in enumerate(holdings):
        with st.expander(f"{h['name']} ({h['ticker']})"):
            c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
            new_qty = c1.number_input("수량", value=h["qty"], key=f"qty_{i}")
            new_avg = c2.number_input("평균단가", value=float(h["avg"]),
                                      key=f"avg_{i}", format="%.2f")
            c3.markdown("<br>", unsafe_allow_html=True)
            if c3.button("수정", key=f"upd_{i}", use_container_width=True):
                update_holding(h["id"], new_qty, new_avg)
                st.success("수정됨")
                st.rerun()
            c4.markdown("<br>", unsafe_allow_html=True)
            if c4.button("🗑️ 삭제", key=f"del_{i}",
                         use_container_width=True, type="secondary"):
                delete_holding(h["id"])
                st.rerun()
else:
    st.info("등록된 종목이 없습니다.")
