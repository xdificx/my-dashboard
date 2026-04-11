import streamlit as st
import pandas as pd
from datetime import datetime
from services.data_service import get_history
from services.db_service import get_all_holdings
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(
    page_title="Chart",
    page_icon="📈",
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
    # ── 종목 선택 + 차트 유형 선택 ──────────────────────
    sel_col, per_col = st.columns([2, 3])

    with sel_col:
        selected = st.selectbox("종목 선택", [h["name"] for h in holdings])

    with per_col:
        # 삼성증권 기준: 5분 / 일 / 주 / 월 / 년
        chart_type = st.radio(
            "차트 유형",
            ["5분", "일", "주", "월", "년"],
            horizontal=True,
            index=1,
        )

    # 차트 유형별 period / interval 매핑
    TYPE_MAP = {
        "5분": {"period": "1d",  "interval": "5m",  "label": "당일 5분봉"},
        "일":  {"period": "3mo", "interval": "1d",  "label": "일봉 (3개월)"},
        "주":  {"period": "1y",  "interval": "1wk", "label": "주봉 (1년)"},
        "월":  {"period": "5y",  "interval": "1mo", "label": "월봉 (5년)"},
        "년":  {"period": "max", "interval": "3mo", "label": "분기봉 (전체)"},
    }

    cfg    = TYPE_MAP[chart_type]
    ticker = next(h["ticker"] for h in holdings if h["name"] == selected)

    # 5분봉은 캐시 무효화 (실시간에 가깝게)
    if chart_type == "5분":
        st.cache_data.clear()

    hist = get_history(ticker, period=cfg["period"], interval=cfg["interval"])

    if not hist.empty:
        if isinstance(hist.columns, pd.MultiIndex):
            hist.columns = hist.columns.get_level_values(0)

        # ── 캔들 + 거래량 차트 ──────────────────────────
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            row_heights=[0.75, 0.25],
            vertical_spacing=0.03,
        )

        fig.add_trace(go.Candlestick(
            x=hist.index,
            open=hist["Open"],  high=hist["High"],
            low=hist["Low"],    close=hist["Close"],
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

        # 5분봉이면 x축 시간 포맷
        if chart_type == "5분":
            fig.update_xaxes(tickformat="%H:%M", row=2, col=1)

        fig.update_layout(
            title=dict(
                text=f"{selected}  —  {cfg['label']}",
                font=dict(size=14),
            ),
            xaxis_rangeslider_visible=False,
            height=560,
            margin=dict(t=40, b=20, l=0, r=0),
            hovermode="x unified",
        )
        fig.update_yaxes(title_text="가격",   row=1, col=1)
        fig.update_yaxes(title_text="거래량",  row=2, col=1)

        st.plotly_chart(fig, use_container_width=True)

        # ── 기간 통계 ──────────────────────────────────
        st.markdown("---")
        try:
            close_last  = float(hist["Close"].iloc[-1])
            close_first = (float(hist["Open"].iloc[0])
                           if chart_type == "5분"
                           else float(hist["Close"].iloc[0]))
            period_ret  = (close_last - close_first) / close_first * 100

            label_ret = "당일 등락률" if chart_type == "5분" else "기간 수익률"

            s1, s2, s3, s4 = st.columns(4)
            s1.metric("현재가",    f"{close_last:,.2f}")
            s2.metric("기간 고가", f"{float(hist['High'].max()):,.2f}")
            s3.metric("기간 저가", f"{float(hist['Low'].min()):,.2f}")
            s4.metric(label_ret,   f"{period_ret:+.2f}%",
                      delta_color="normal" if period_ret >= 0 else "inverse")

            if chart_type == "5분":
                st.caption(
                    "⚠️ 5분봉 데이터는 yfinance 기준 UTC 시각으로 표시될 수 있습니다. "
                    "국내 종목은 실제 거래 시간과 9시간 차이가 날 수 있어요."
                )
        except Exception:
            pass

    else:
        if chart_type == "5분":
            st.warning(
                "당일 5분봉 데이터를 불러오지 못했습니다.\n\n"
                "장 마감 후이거나 휴장일일 수 있습니다."
            )
        else:
            st.warning("차트 데이터를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.")
