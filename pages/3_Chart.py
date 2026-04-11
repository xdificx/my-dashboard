import streamlit as st
import pandas as pd
from datetime import datetime
from services.data_service import get_history
from services.db_service import get_all_holdings
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(
    page_title="Chart",
    layout="wide",
)

with st.sidebar:
    st.markdown("### ⚙️ 설정")
    st.caption(f"갱신 시각\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

st.markdown("""
<div style="padding:8px 0 4px 0;">
  <span style="font-size:28px;font-weight:800;">📈 Chart</span>
</div>
<div style="font-size:12px;color:#888;margin-bottom:16px;">
  종목별 캔들차트 및 거래량
</div>
""", unsafe_allow_html=True)

holdings = get_all_holdings()

if not holdings:
    st.info("Portfolio 페이지에서 종목을 추가해주세요.")
else:
    # 종목 선택 + 기간 선택
    sel_col, per_col = st.columns([2, 3])
    with sel_col:
        selected = st.selectbox("종목 선택", [h["name"] for h in holdings])
    with per_col:
        period = st.radio("기간", ["1mo","3mo","6mo","1y","2y"],
                          horizontal=True, index=3)

    ticker = next(h["ticker"] for h in holdings if h["name"] == selected)
    hist   = get_history(ticker, period=period)

    if not hist.empty:
        if isinstance(hist.columns, pd.MultiIndex):
            hist.columns = hist.columns.get_level_values(0)

        # 상승/하락 색상 (증권사 앱 기준)
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            row_heights=[0.75, 0.25],
            vertical_spacing=0.03,
        )
        fig.add_trace(go.Candlestick(
            x=hist.index,
            open=hist["Open"], high=hist["High"],
            low=hist["Low"],   close=hist["Close"],
            increasing_line_color="#e24b4a",
            decreasing_line_color="#378add",
            name="가격",
        ), row=1, col=1)
        fig.add_trace(go.Bar(
            x=hist.index,
            y=hist["Volume"],
            marker_color="#cccccc",
            name="거래량",
        ), row=2, col=1)
        fig.update_layout(
            xaxis_rangeslider_visible=False,
            height=560,
            margin=dict(t=20, b=20, l=0, r=0),
            hovermode="x unified",
        )
        fig.update_yaxes(title_text="가격", row=1, col=1)
        fig.update_yaxes(title_text="거래량", row=2, col=1)

        st.plotly_chart(fig, use_container_width=True)

        # 기본 통계
        st.markdown("---")
        last = hist.iloc[-1]
        first = hist.iloc[0]
        period_ret = (float(last["Close"]) - float(first["Close"])) / float(first["Close"]) * 100
        ret_color  = "#e24b4a" if period_ret >= 0 else "#378add"
        ret_arrow  = "▲" if period_ret >= 0 else "▼"

        s1, s2, s3, s4 = st.columns(4)
        s1.metric("현재가",   f"{float(last['Close']):,.2f}")
        s2.metric("기간 고가", f"{float(hist['High'].max()):,.2f}")
        s3.metric("기간 저가", f"{float(hist['Low'].min()):,.2f}")
        s4.metric("기간 수익률",
                  f"{period_ret:+.2f}%",
                  delta_color="normal" if period_ret >= 0 else "inverse")
    else:
        st.warning("차트 데이터를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.")
