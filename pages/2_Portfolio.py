import streamlit as st
import pandas as pd
from datetime import datetime, date
from services.data_service import get_ticker_data
from services.db_service import (
    get_all_transactions, add_transaction, delete_transaction,
    get_current_holdings, get_closed_positions
)
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
#  헤더 + 버튼 (우측 상단)
# ══════════════════════════════════════════════════
hdr_col, buy_col, sell_col = st.columns([4, 1, 1])

with hdr_col:
    st.markdown("""
<div style="padding:8px 0 4px 0;">
  <span style="font-size:28px;font-weight:800;">💼 Portfolio</span>
</div>
<div style="font-size:12px;color:#888;margin-bottom:8px;">
  데이터: Yahoo Finance | 15분 지연
</div>
""", unsafe_allow_html=True)

with buy_col:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("📈 ADD 매수", use_container_width=True):
        st.session_state["form_mode"] = (
            None if st.session_state.get("form_mode") == "buy" else "buy"
        )

with sell_col:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("📉 ADD 매도", use_container_width=True):
        st.session_state["form_mode"] = (
            None if st.session_state.get("form_mode") == "sell" else "sell"
        )

# ══════════════════════════════════════════════════
#  매수 / 매도 입력 폼
# ══════════════════════════════════════════════════
mode = st.session_state.get("form_mode")

if mode in ("buy", "sell"):
    label     = "📈 매수 종목 추가" if mode == "buy" else "📉 매도 종목 추가"
    btn_color = "#e24b4a" if mode == "buy" else "#378add"

    with st.container(border=True):
        st.markdown(
            f'<div style="font-size:15px;font-weight:700;color:{btn_color};'
            f'margin-bottom:8px;">{label}</div>',
            unsafe_allow_html=True
        )
        c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([1.5, 1.5, 1, 1.5, 1, 1, 1.2, 1])

        f_ticker = c1.text_input("티커", placeholder="005930.KS", key="f_ticker")
        f_name   = c2.text_input("종목명", placeholder="삼성전자",  key="f_name")
        f_qty    = c3.number_input("수량", min_value=0.0001, value=1.0,
                                   format="%.4f", key="f_qty")
        f_price  = c4.number_input(
            "매수가" if mode == "buy" else "매도가",
            min_value=0.0, value=0.0, format="%.2f", key="f_price"
        )
        f_date   = c5.date_input(
            "매수일" if mode == "buy" else "매도일",
            value=date.today(), key="f_date"
        )
        f_market = c6.selectbox("시장", ["KR", "US"], key="f_market")
        c7.markdown("<div style='font-size:12px;color:#555;margin-bottom:4px;'>ETF 여부</div>",
                    unsafe_allow_html=True)
        f_is_etf = c7.checkbox("ETF", value=False, key="f_is_etf",
                               label_visibility="collapsed")
        c8.markdown("<br>", unsafe_allow_html=True)
        if c8.button("저장", key="save_btn", use_container_width=True):
            if f_ticker and f_name and f_price > 0:
                add_transaction({
                    "ticker":  f_ticker.strip(),
                    "name":    f_name.strip(),
                    "market":  f_market,
                    "is_etf":  f_is_etf,
                    "type":    mode,
                    "qty":     float(f_qty),
                    "price":   float(f_price),
                    "date":    str(f_date),
                })
                act = "매수" if mode == "buy" else "매도"
                st.success(f"{f_name} {act} 내역 저장됨")
                st.session_state["form_mode"] = None
                st.rerun()
            else:
                st.warning("티커, 종목명, 매수/매도가를 모두 입력해주세요.")

# 환율
fx = get_ticker_data("USDKRW=X")
FX = fx["price"] if fx.get("ok") else 1330.0

# ══════════════════════════════════════════════════
#  탭
# ══════════════════════════════════════════════════
tab1, tab2, tab3 = st.tabs(["📊 현재 보유 종목", "✅ 매도 완료 종목", "📋 전체 거래 이력"])

# ─────────────────────────────────────────────────
#  탭 1 — 현재 보유 종목
# ─────────────────────────────────────────────────
with tab1:
    holdings = get_current_holdings()

    if not holdings:
        st.info("매수 내역을 추가하면 보유 종목이 표시됩니다.")
    else:
        rows = []
        for h in holdings:
            d = get_ticker_data(h["ticker"])
            if d.get("ok"):
                row = calculate_portfolio_row(h, d["price"], FX)
                rows.append(row)
            else:
                rows.append({
                    "종목":       h["name"],
                    "현재가":     "조회 실패",
                    "수량":       h["qty"],
                    "평가금액(원)": "-",
                    "평가손익(원)": "-",
                    "수익률(%)":  None,
                })

        df = pd.DataFrame(rows)

        def _style(v):
            if not isinstance(v, (int, float)): return ""
            return "color:#e24b4a;font-weight:600" if v > 0 else "color:#378add;font-weight:600"

        st.dataframe(
            df.style.map(_style, subset=["수익률(%)"]),
            use_container_width=True, hide_index=True,
        )

        try:
            total_val  = sum(
                int(str(r["평가금액(원)"]).replace(",",""))
                for r in rows if r["평가금액(원)"] != "-"
            )
            total_cost = sum(
                (round(h["avg_price"] * FX) if h["market"] == "US"
                 else round(h["avg_price"])) * h["qty"]
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
            c4.metric("총 수익률",   f"{total_ret:+.2f}%",
                      delta_color="normal" if total_ret >= 0 else "inverse")
            st.caption(f"적용 환율: 1 USD = {FX:,.2f} KRW")
        except Exception:
            pass

# ─────────────────────────────────────────────────
#  탭 2 — 매도 완료 종목
# ─────────────────────────────────────────────────
with tab2:
    closed = get_closed_positions()

    if not closed:
        st.info("매도 완료된 종목이 없습니다.")
    else:
        rows_c = []
        for c in closed:
            pnl_krw = (round(c["realized_pnl"] * FX)
                       if c["market"] == "US" else round(c["realized_pnl"]))
            rows_c.append({
                "종목명":       c["name"],
                "시장":         c["market"],
                "수량":         c["qty"],
                "평균 매수가":  f"{c['avg_buy']:,.2f}",
                "평균 매도가":  f"{c['avg_sell']:,.2f}",
                "실현 손익(원)": pnl_krw,
                "수익률(%)":    c["return_pct"],
                "보유 기간(일)": c["hold_days"],
                "매수일":       c["first_buy"],
                "매도일":       c["last_sell"],
            })

        df_c = pd.DataFrame(rows_c)

        def _style_c(v):
            if not isinstance(v, (int, float)): return ""
            return "color:#e24b4a;font-weight:600" if v > 0 else "color:#378add;font-weight:600"

        st.dataframe(
            df_c.style.map(_style_c, subset=["실현 손익(원)", "수익률(%)"]),
            use_container_width=True, hide_index=True,
        )

        total_pnl_c = sum(r["실현 손익(원)"] for r in rows_c)
        pnl_color   = "#e24b4a" if total_pnl_c >= 0 else "#378add"
        st.markdown(
            f'<div style="font-size:14px;font-weight:600;color:{pnl_color};'
            f'margin-top:8px;">누적 실현 손익: {total_pnl_c:+,.0f}원</div>',
            unsafe_allow_html=True
        )

# ─────────────────────────────────────────────────
#  탭 3 — 전체 거래 이력
# ─────────────────────────────────────────────────
with tab3:
    transactions = get_all_transactions()

    if not transactions:
        st.info("거래 내역이 없습니다.")
    else:
        rows_t = []
        for t in transactions:
            rows_t.append({
                "ID":      t["id"],
                "날짜":    t["date"],
                "구분":    "📈 매수" if t["type"] == "buy" else "📉 매도",
                "종목명":  t["name"],
                "티커":    t["ticker"],
                "시장":    t["market"],
                "ETF":     "✓" if t.get("is_etf") else "",
                "수량":    t["qty"],
                "단가":    f"{float(t['price']):,.2f}",
                "거래금액": f"{float(t['qty']) * float(t['price']):,.0f}",
            })

        df_t = pd.DataFrame(rows_t)

        def _style_t(v):
            if not isinstance(v, str): return ""
            if "매수" in v: return "color:#e24b4a;font-weight:600"
            if "매도" in v: return "color:#378add;font-weight:600"
            return ""

        st.dataframe(
            df_t.style.map(_style_t, subset=["구분"]),
            use_container_width=True, hide_index=True,
        )

        st.markdown("---")
        with st.expander("🗑️ 거래 내역 삭제 (잘못 입력한 경우)"):
            st.caption("위 테이블의 ID를 확인 후 입력하세요.")
            del_id = st.number_input("삭제할 ID", min_value=1, step=1, key="del_id")
            if st.button("삭제 확인", type="secondary", key="del_btn"):
                delete_transaction(int(del_id))
                st.success(f"ID {del_id} 삭제됨")
                st.rerun()
