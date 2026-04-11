import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
from services.data_service import get_ticker_data, get_history
from services.db_service import get_all_holdings
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


def fetch(ticker, label):
    d = get_ticker_data(ticker)
    d["label"] = label
    return d

# ══════════════════════════════════════════════════
#  사이드바
# ══════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### ⚙️ 설정")
    auto_refresh = st.toggle("5분 자동 갱신", value=True)
    st.divider()
    # 하단 여백을 밀어넣어 데이터 출처를 최하단에 고정
    st.markdown(
        """<div style="position:fixed;bottom:20px;font-size:11px;color:#aaa;line-height:1.6;">
        데이터: Yahoo Finance (yfinance)<br>
        15분 지연<br>
        갱신 시각: {now}
        </div>""".format(now=__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
        unsafe_allow_html=True
    )

fx = fetch("USDKRW=X", "원/달러 환율")
FX = fx["price"] if fx.get("ok") else 1330.0

# ══════════════════════════════════════════════════
#  섹션 1 — Market Indicator
# ══════════════════════════════════════════════════
st.markdown("### 📈 Market Indicator")
col_kr, col_us, col_macro = st.columns([1, 1, 1], gap="small")

with col_kr:
    st.markdown(
        '<div style="background:#fff5f5;border-radius:12px;padding:14px 16px 6px 16px;">'
        '<div style="font-size:13px;font-weight:700;margin-bottom:8px;">🇰🇷 국내 지수</div>',
        unsafe_allow_html=True)
    for t, n in [("^KS11","KOSPI"),("^KQ11","KOSDAQ"),("^KS200","KOSPI 200")]:
        show_card(fetch(t, n))
    st.markdown('</div>', unsafe_allow_html=True)

with col_us:
    st.markdown(
        '<div style="background:#f5f8ff;border-radius:12px;padding:14px 16px 6px 16px;">'
        '<div style="font-size:13px;font-weight:700;margin-bottom:8px;">🌎 해외 지수</div>',
        unsafe_allow_html=True)
    for t, n in [("^GSPC","S&P 500"),("^IXIC","나스닥"),("^DJI","다우존스")]:
        show_card(fetch(t, n))
    st.markdown('</div>', unsafe_allow_html=True)

with col_macro:
    st.markdown(
        '<div style="background:#f5f5f5;border-radius:12px;padding:14px 16px 6px 16px;">'
        '<div style="font-size:13px;font-weight:700;margin-bottom:8px;">📡 거시 지표</div>',
        unsafe_allow_html=True)
    for t, n in [("USDKRW=X","원/달러 환율"),("^TNX","미 10년 국채"),("^VIX","변동성 (VIX)")]:
        show_card(fetch(t, n))
    st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# ══════════════════════════════════════════════════
#  섹션 2 — 포트폴리오 총계
# ══════════════════════════════════════════════════
st.markdown("### 💼 포트폴리오 총계")
holdings = get_all_holdings()

if not holdings:
    st.info("Portfolio 페이지에서 종목을 추가해주세요.")
else:
    rows = []
    for h in holdings:
        d = get_ticker_data(h["ticker"])
        if d.get("ok"):
            rows.append(calculate_portfolio_row(h, d["price"], FX))

    if rows:
        try:
            total_val  = sum(int(str(r["평가금액(원)"]).replace(",","")) for r in rows)
            total_cost = sum(
                (round(h["avg"] * FX) if h["market"] == "US" else round(h["avg"])) * h["qty"]
                for h in holdings
            )
            total_pnl = total_val - total_cost
            total_ret = total_pnl / total_cost * 100 if total_cost else 0

            c1, c2, c3, c4 = st.columns(4)
            pnl_color  = "#e24b4a" if total_pnl >= 0 else "#378add"
            ret_arrow  = "▲" if total_ret >= 0 else "▼"

            c1.metric("총 투자금액", f"{total_cost:,.0f}원")
            c2.metric("총 평가금액", f"{total_val:,.0f}원")
            c3.metric("총 평가손익", f"{total_pnl:+,.0f}원",
                      delta_color="normal" if total_pnl >= 0 else "inverse")
            c4.metric("총 수익률", f"{total_ret:+.2f}%",
                      delta_color="normal" if total_ret >= 0 else "inverse")
            st.caption(f"적용 환율: 1 USD = {FX:,.2f} KRW")
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
    def build_portfolio_history(tickers_market_avg_qty, period, fx_rate):
        """날짜별 포트폴리오 총 평가금액 및 수익률 계산"""
        all_closes = {}
        for ticker, market, avg, qty in tickers_market_avg_qty:
            try:
                df = yf.download(ticker, period=period, interval="1d", progress=False)
                if df.empty:
                    continue
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                all_closes[ticker] = (df["Close"], market, avg, qty)
            except Exception:
                continue

        if not all_closes:
            return pd.DataFrame()

        # 공통 날짜 기준으로 맞추기
        dates = None
        for ticker, (series, *_) in all_closes.items():
            dates = series.index if dates is None else dates.intersection(series.index)

        if dates is None or len(dates) == 0:
            return pd.DataFrame()

        total_cost = sum(
            (round(avg * fx_rate) if market == "US" else round(avg)) * qty
            for _, market, avg, qty in all_closes.values()
        )

        daily_val = []
        for date in dates:
            val = 0
            for ticker, (series, market, avg, qty) in all_closes.items():
                try:
                    price = float(series.loc[date])
                    cur = round(price * fx_rate) if market == "US" else round(price)
                    val += cur * qty
                except Exception:
                    continue
            daily_val.append({"date": date, "total_val": val})

        df_result = pd.DataFrame(daily_val).set_index("date")
        df_result["수익률(%)"] = (df_result["total_val"] - total_cost) / total_cost * 100
        df_result["평가금액(원)"] = df_result["total_val"]
        return df_result

    tickers_info = tuple(
        (h["ticker"], h["market"], h["avg"], h["qty"])
        for h in holdings
    )

    with st.spinner("수익률 데이터 불러오는 중..."):
        hist_df = build_portfolio_history(tickers_info, period_opt, FX)

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
