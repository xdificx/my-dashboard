import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
from services.data_service import get_ticker_data, get_history, get_multiple_tickers, get_holdings_prices
from services.db_service import get_all_holdings, get_current_holdings, get_all_transactions, get_cash_summary
from services.calculations import calculate_portfolio_row
import plotly.graph_objects as go

st.set_page_config(
    page_title="Main Dashboard",
    page_icon="📈",
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


# ══════════════════════════════════════════════════
#  사이드바
# ══════════════════════════════════════════════════
with st.sidebar:
    # ── 날짜·시간 (한 줄) ─────────────────────────
    now = datetime.now()
    weekday = ["월","화","수","목","금","토","일"][now.weekday()]
    st.markdown(f"""
<div style="padding:8px 0 6px 0;font-size:13px;color:#555;font-weight:600;">
  {now.strftime('%Y.%m.%d')}({weekday}) &nbsp; {now.strftime('%H:%M:%S')}
</div>
""", unsafe_allow_html=True)

    st.divider()

    # ── 연동 상태 ──────────────────────────────────
    st.markdown("**연동 상태**")

    @st.cache_data(ttl=60)
    def _check_yfinance():
        try:
            p = yf.Ticker("^GSPC").fast_info.last_price
            return p and p > 0
        except Exception:
            return False

    @st.cache_data(ttl=60)
    def _check_supabase():
        try:
            from services.supabase_client import supabase
            supabase.table("transactions").select("id").limit(1).execute()
            return True
        except Exception:
            return False

    @st.cache_data(ttl=60)
    def _check_render():
        try:
            import os
            return os.environ.get("RENDER") is not None or True
        except Exception:
            return False

    yf_ok     = _check_yfinance()
    db_ok     = _check_supabase()
    render_ok = _check_render()

    def _row(ok: bool, label: str) -> str:
        dot    = "🟢" if ok else "🔴"
        color  = "#333" if ok else "#e24b4a"
        status = "정상" if ok else "연결 실패"
        return (f'<div style="display:flex;justify-content:space-between;'
                f'font-size:13px;padding:3px 0;">'
                f'<span>{dot} {label}</span>'
                f'<span style="color:{color};font-size:11px;">{status}</span></div>')

    st.markdown(
        _row(render_ok, "Render 서버") +
        _row(yf_ok,     "Yahoo Finance") +
        _row(db_ok,     "Supabase DB"),
        unsafe_allow_html=True
    )

    if not all([render_ok, yf_ok, db_ok]):
        st.caption("연결 실패 항목이 있습니다.")

    st.divider()

    # ── 설정 ───────────────────────────────────────
    st.markdown("**설정**")
    auto_refresh = st.toggle("5분 자동 갱신", value=True)

    st.divider()

    # ── 하단 고정: 데이터 출처 ─────────────────────
    st.markdown(
        """<div style="position:fixed;bottom:20px;left:0;width:18rem;
                       padding:0 1.5rem;box-sizing:border-box;
                       font-size:12px;color:#aaa;line-height:1.8;">
        데이터: Yahoo Finance<br>
        15분 지연<br>
        최종 갱신: {now}
        </div>""".format(now=now.strftime('%Y-%m-%d %H:%M')),
        unsafe_allow_html=True
    )

# ══════════════════════════════════════════════════
#  종목 분류 함수 (도넛 차트용)
# ══════════════════════════════════════════════════
def classify_holding(h: dict) -> str:
    market = h.get("market", "KR")
    is_etf = h.get("is_etf", False)
    if market == "KR":
        return "국내 ETF" if is_etf else "국내 개별 종목"
    else:
        return "해외 ETF" if is_etf else "해외 개별 종목"

# ══════════════════════════════════════════════════
#  섹션 1 — Market Indicator + 도넛 차트 (병렬 로딩)
# ══════════════════════════════════════════════════

# 모든 Market Indicator 티커를 한 번에 병렬 조회
MARKET_TICKERS = (
    ("USDKRW=X", "원/달러 환율"),
    ("^KS11",    "KOSPI"),
    ("^KQ11",    "KOSDAQ"),
    ("^KS200",   "KOSPI 200"),
    ("^GSPC",    "S&P 500"),
    ("^IXIC",    "나스닥"),
    ("^DJI",     "다우존스"),
    ("^TNX",     "미 10년 국채"),
    ("^VIX",     "변동성 (VIX)"),
)

with st.spinner("시장 데이터 불러오는 중..."):
    market_data = get_multiple_tickers(MARKET_TICKERS)

fx_d = market_data.get("USDKRW=X", {})
FX   = fx_d.get("price") or 1330.0

left_col, right_col = st.columns([3, 2], gap="medium")

with left_col:
    st.markdown("### 📈 Market Indicator")
    col_kr, col_us, col_macro = st.columns([1, 1, 1], gap="small")

    with col_kr:
        st.markdown(
            '<div style="background:#fff5f5;border-radius:12px;padding:14px 16px 6px 16px;">'
            '<div style="font-size:13px;font-weight:700;margin-bottom:8px;">🇰🇷 국내 지수</div>',
            unsafe_allow_html=True)
        for t in ["^KS11","^KQ11","^KS200"]:
            show_card(market_data.get(t, {"label": t, "ok": False}))
        st.markdown('</div>', unsafe_allow_html=True)

    with col_us:
        st.markdown(
            '<div style="background:#f5f8ff;border-radius:12px;padding:14px 16px 6px 16px;">'
            '<div style="font-size:13px;font-weight:700;margin-bottom:8px;">🌎 해외 지수</div>',
            unsafe_allow_html=True)
        for t in ["^GSPC","^IXIC","^DJI"]:
            show_card(market_data.get(t, {"label": t, "ok": False}))
        st.markdown('</div>', unsafe_allow_html=True)

    with col_macro:
        st.markdown(
            '<div style="background:#f5f5f5;border-radius:12px;padding:14px 16px 6px 16px;">'
            '<div style="font-size:13px;font-weight:700;margin-bottom:8px;">📡 거시 지표</div>',
            unsafe_allow_html=True)
        for t in ["USDKRW=X","^TNX","^VIX"]:
            show_card(market_data.get(t, {"label": t, "ok": False}))
        st.markdown('</div>', unsafe_allow_html=True)

with right_col:
    st.markdown("### 🥧 자산 배분")
    holdings_for_donut = get_all_holdings()

    if not holdings_for_donut:
        st.info("Portfolio 페이지에서 종목을 추가하면 자산 배분 차트가 표시됩니다.")
    else:
        # 카테고리별 투자금액 합산
        # 4개 카테고리 항상 고정 표시 (0원도 포함)
        CATEGORIES  = ["국내 개별 종목", "국내 ETF", "해외 개별 종목", "해외 ETF"]
        DONUT_COLORS = ["#e24b4a", "#ffaaaa", "#378add", "#99c2ee"]

        category_amounts = {c: 0 for c in CATEGORIES}
        for h in holdings_for_donut:
            cat  = classify_holding(h)
            cost = (round(h["avg"] * FX) if h["market"] == "US" else round(h["avg"])) * h["qty"]
            category_amounts[cat] += cost

        labels     = CATEGORIES
        values     = [category_amounts[c] for c in CATEGORIES]
        total_cost = sum(values)

        fig_donut = go.Figure(go.Pie(
            labels=labels,
            values=[max(v, 1) for v in values],   # 0이면 1로 대체해 조각 유지
            hole=0.58,
            pull=[0.03 if v > 0 else 0 for v in values],
            marker=dict(
                colors=[c if values[i] > 0 else "#eeeeee"
                        for i, c in enumerate(DONUT_COLORS)],
                line=dict(color="#fff", width=2),
            ),
            textinfo="none",
            hovertemplate="%{label}<br>%{customdata:,.0f}원<br>%{percent}<extra></extra>",
            customdata=values,
        ))

        donut_col, legend_col = st.columns([3, 2])

        with donut_col:
            fig_donut.update_layout(
                height=300,
                margin=dict(t=10, b=10, l=0, r=0),
                showlegend=False,
            )
            st.plotly_chart(fig_donut, use_container_width=True)

        with legend_col:
            st.markdown("<br><br>", unsafe_allow_html=True)
            for label, val, color in zip(labels, values, DONUT_COLORS):
                pct        = val / total_cost * 100 if total_cost > 0 else 0
                text_color = "#333" if val > 0 else "#bbb"
                box_color  = color if val > 0 else "#eeeeee"
                st.markdown(f"""
<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
  <div style="width:12px;height:12px;border-radius:3px;
              background:{box_color};flex-shrink:0;"></div>
  <div style="font-size:12px;line-height:1.5;">
    <div style="color:{text_color};font-weight:600;">{label}</div>
    <div style="color:{text_color};">{val:,.0f}원</div>
    <div style="color:#aaa;">{pct:.1f}%</div>
  </div>
</div>""", unsafe_allow_html=True)

st.divider()

# ══════════════════════════════════════════════════
#  섹션 2 — 포트폴리오 총계 (병렬 조회)
# ══════════════════════════════════════════════════
st.markdown("### 💼 포트폴리오 총계")
holdings = get_all_holdings()

if not holdings:
    st.info("Portfolio 페이지에서 종목을 추가해주세요.")
else:
    with st.spinner("보유 종목 현재가 조회 중..."):
        tickers_tuple = tuple(h["ticker"] for h in holdings)
        prices = get_holdings_prices(tickers_tuple)

    rows = []
    for h in holdings:
        price = prices.get(h["ticker"])
        if price:
            rows.append(calculate_portfolio_row(h, price, FX))

    if rows:
        try:
            total_val  = sum(int(str(r["평가금액(원)"]).replace(",","")) for r in rows)
            total_cost = sum(
                (round(h["avg"] * FX) if h["market"] == "US" else round(h["avg"])) * h["qty"]
                for h in holdings
            )
            total_pnl = total_val - total_cost
            total_ret = total_pnl / total_cost * 100 if total_cost else 0

            cash = get_cash_summary()

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("순수 현금 투자액", f"{cash['net_cash']:,.0f}원",
                      help="총 입금액 - 총 출금액")
            c2.metric("총 매수금액",  f"{total_cost:,.0f}원")
            c3.metric("총 평가금액",  f"{total_val:,.0f}원")
            c4.metric("총 평가손익",  f"{total_pnl:+,.0f}원",
                      delta_color="normal" if total_pnl >= 0 else "inverse")
            c5.metric("총 수익률",    f"{total_ret:+.2f}%",
                      delta_color="normal" if total_ret >= 0 else "inverse")
            st.caption(f"적용 환율: 1 USD = {FX:,.2f} KRW  |  "
                       f"입출금 내역은 Portfolio → 💰 입출금 관리 탭에서 입력하세요.")
        except Exception:
            pass

st.divider()

# ══════════════════════════════════════════════════
#  섹션 3 — 일별 수익률 변화 차트
# ══════════════════════════════════════════════════
st.markdown("### 📉 일별 수익률 변화")

if not holdings:
    st.info("Portfolio 페이지에서 종목을 추가하면 수익률 차트가 표시됩니다.")
else:
    period_opt = st.radio("기간", ["1mo","3mo","6mo","1y"], horizontal=True, index=1)

    # 각 종목의 히스토리 불러와서 날짜별 포트폴리오 평가금액 계산
    import yfinance as yf

    @st.cache_data(ttl=300)
    def build_portfolio_history(tx_tuple, period, fx_rate):
        """
        거래 이력 기반 날짜별 포트폴리오 수익률 계산
        - 매수일 이전 데이터 제외
        - 매도 후 잔여 수량만 반영
        """
        import pandas as pd
        from datetime import datetime, timedelta

        transactions = list(tx_tuple)  # tuple → list 복원
        if not transactions:
            return pd.DataFrame()

        # 기간 설정
        period_days = {"1mo":30,"3mo":90,"6mo":180,"1y":365}
        days = period_days.get(period, 90)
        end_date   = datetime.today().date()
        start_date = end_date - timedelta(days=days)

        # ticker별 가격 히스토리 다운로드
        tickers = list({t["ticker"] for t in transactions})
        price_data = {}
        for ticker in tickers:
            try:
                df = yf.download(ticker, start=str(start_date), end=str(end_date),
                                 interval="1d", progress=False)
                if df.empty:
                    continue
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                price_data[ticker] = df["Close"]
            except Exception:
                continue

        if not price_data:
            return pd.DataFrame()

        # 공통 날짜 추출
        all_dates = None
        for series in price_data.values():
            all_dates = series.index if all_dates is None else all_dates.union(series.index)

        if all_dates is None or len(all_dates) == 0:
            return pd.DataFrame()

        # 날짜별 포트폴리오 계산
        daily_val  = []
        daily_cost = []

        for d in all_dates:
            d_str = d.strftime("%Y-%m-%d") if hasattr(d, 'strftime') else str(d)[:10]

            # 이 날짜 기준 보유 수량 및 평균단가 계산
            holdings_on_date = {}
            for t in transactions:
                t_date = str(t["date"])[:10]
                if t_date > d_str:
                    continue  # 이 날짜 이후 거래는 제외
                ticker = t["ticker"]
                if ticker not in holdings_on_date:
                    holdings_on_date[ticker] = {
                        "market": t["market"],
                        "buy_qty": 0.0, "buy_amount": 0.0,
                        "sell_qty": 0.0,
                    }
                if t["type"] == "buy":
                    holdings_on_date[ticker]["buy_qty"]    += float(t["qty"])
                    holdings_on_date[ticker]["buy_amount"] += float(t["qty"]) * float(t["price"])
                elif t["type"] == "sell":
                    holdings_on_date[ticker]["sell_qty"]   += float(t["qty"])

            val  = 0.0
            cost = 0.0
            for ticker, h in holdings_on_date.items():
                remain = h["buy_qty"] - h["sell_qty"]
                if remain <= 0:
                    continue
                avg = h["buy_amount"] / h["buy_qty"] if h["buy_qty"] > 0 else 0
                # 평가금액
                if ticker in price_data:
                    try:
                        price = float(price_data[ticker].loc[d])
                        cur   = round(price * fx_rate) if h["market"] == "US" else round(price)
                        val  += cur * remain
                    except Exception:
                        cur   = round(avg * fx_rate) if h["market"] == "US" else round(avg)
                        val  += cur * remain
                # 투자 원금
                cost_unit = round(avg * fx_rate) if h["market"] == "US" else round(avg)
                cost += cost_unit * remain

            if cost > 0:
                daily_val.append({"date": d, "total_val": val, "total_cost": cost})

        if not daily_val:
            return pd.DataFrame()

        df_result = pd.DataFrame(daily_val).set_index("date")
        df_result["수익률(%)"]  = (df_result["total_val"] - df_result["total_cost"]) / df_result["total_cost"] * 100
        df_result["평가금액(원)"] = df_result["total_val"]
        return df_result

    # transactions를 tuple로 변환해서 캐시 키로 사용
    transactions = get_all_transactions()
    tx_tuple = tuple(
        (t["ticker"], t["type"], t["qty"], t["price"], t["date"], t["market"])
        for t in transactions
    )

    with st.spinner("수익률 데이터 불러오는 중..."):
        hist_df = build_portfolio_history(tx_tuple, period_opt, FX)

    if not hist_df.empty:
        fig = go.Figure()

        # 수익률 0% 기준선
        fig.add_hline(y=0, line_dash="dash", line_color="#aaaaaa", line_width=1)

        # 수익률 라인
        colors = ["#e24b4a" if v >= 0 else "#378add" for v in hist_df["수익률(%)"]]
        fig.add_trace(go.Scatter(
            x=hist_df.index,
            y=hist_df["수익률(%)"],
            mode="lines",
            line=dict(width=2, color="#e24b4a"),
            fill="tozeroy",
            fillcolor="rgba(226,75,74,0.08)",
            name="수익률(%)",
            hovertemplate="%{x|%Y-%m-%d}<br>수익률: %{y:.2f}%<extra></extra>",
        ))

        fig.update_layout(
            height=320,
            margin=dict(t=10, b=20, l=0, r=0),
            yaxis=dict(ticksuffix="%", zeroline=False),
            xaxis=dict(showgrid=False),
            showlegend=False,
            hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True)

        # 현재 수익률 요약
        latest_ret = hist_df["수익률(%)"].iloc[-1]
        latest_val = hist_df["평가금액(원)"].iloc[-1]
        ret_color  = "#e24b4a" if latest_ret >= 0 else "#378add"
        ret_arrow  = "▲" if latest_ret >= 0 else "▼"
        st.markdown(
            f'<div style="font-size:13px;color:#888;">최근 기준: '
            f'<span style="color:{ret_color};font-weight:700;">'
            f'{ret_arrow} {abs(latest_ret):.2f}%</span>'
            f' &nbsp;|&nbsp; 평가금액: {latest_val:,.0f}원</div>',
            unsafe_allow_html=True
        )
    else:
        st.warning("수익률 차트 데이터를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.")

# ══════════════════════════════════════════════════
#  자동 갱신
# ══════════════════════════════════════════════════
if auto_refresh:
    time.sleep(300)
    st.rerun()
