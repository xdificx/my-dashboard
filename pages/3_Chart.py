import streamlit as st
import pandas as pd
import numpy as np
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
  종목별 캔들차트 · 이동평균선 · RSI · MACD
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════
#  지표 계산 함수
# ══════════════════════════════════════════════════
def calc_ma(series, window):
    return series.rolling(window=window).mean()

def calc_rsi(series, period=14):
    delta = series.diff()
    gain  = delta.clip(lower=0)
    loss  = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs  = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calc_macd(series, fast=12, slow=26, signal=9):
    ema_fast   = series.ewm(span=fast,   adjust=False).mean()
    ema_slow   = series.ewm(span=slow,   adjust=False).mean()
    macd_line  = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram  = macd_line - signal_line
    return macd_line, signal_line, histogram

# ══════════════════════════════════════════════════
#  공휴일 목록 (2020~2026)
# ══════════════════════════════════════════════════
KR_HOLIDAYS = [
    "2020-01-01","2020-01-24","2020-01-25","2020-01-26","2020-01-27",
    "2020-03-01","2020-04-15","2020-04-30","2020-05-05","2020-05-25",
    "2020-06-06","2020-08-15","2020-08-17","2020-09-30","2020-10-01",
    "2020-10-02","2020-10-03","2020-10-09","2020-12-25",
    "2021-01-01","2021-02-11","2021-02-12","2021-02-13",
    "2021-03-01","2021-05-05","2021-05-19","2021-06-06",
    "2021-08-15","2021-08-16","2021-09-20","2021-09-21","2021-09-22",
    "2021-10-03","2021-10-04","2021-10-09","2021-10-11","2021-12-25",
    "2022-01-01","2022-01-31","2022-02-01","2022-02-02",
    "2022-03-01","2022-03-09","2022-05-05","2022-05-08","2022-05-16",
    "2022-06-01","2022-06-06","2022-08-15","2022-09-09","2022-09-10",
    "2022-09-11","2022-09-12","2022-10-03","2022-10-09","2022-10-10","2022-12-25",
    "2023-01-01","2023-01-21","2023-01-22","2023-01-23","2023-01-24",
    "2023-03-01","2023-05-01","2023-05-05","2023-05-27","2023-05-29",
    "2023-06-06","2023-08-15","2023-09-28","2023-09-29","2023-09-30",
    "2023-10-02","2023-10-03","2023-10-09","2023-12-25",
    "2024-01-01","2024-02-09","2024-02-10","2024-02-11","2024-02-12",
    "2024-03-01","2024-04-10","2024-05-01","2024-05-05","2024-05-06",
    "2024-05-15","2024-06-06","2024-08-15","2024-09-16","2024-09-17",
    "2024-09-18","2024-10-01","2024-10-03","2024-10-09","2024-12-25",
    "2025-01-01","2025-01-28","2025-01-29","2025-01-30",
    "2025-03-01","2025-03-03","2025-05-01","2025-05-05","2025-05-06",
    "2025-06-03","2025-06-06","2025-08-15","2025-10-03","2025-10-05",
    "2025-10-06","2025-10-07","2025-10-08","2025-10-09","2025-12-25",
    "2026-01-01","2026-02-16","2026-02-17","2026-02-18","2026-02-19",
    "2026-03-01","2026-03-02","2026-05-01","2026-05-05","2026-05-25",
    "2026-06-06","2026-08-15","2026-08-17","2026-09-24","2026-09-25",
    "2026-09-26","2026-09-28","2026-10-03","2026-10-05","2026-10-09","2026-12-25",
]

# ══════════════════════════════════════════════════
#  메인
# ══════════════════════════════════════════════════
holdings = get_all_holdings()

if not holdings:
    st.info("Portfolio 페이지에서 종목을 추가해주세요.")
else:
    # ── 종목·차트 유형 선택 ────────────────────────────
    sel_col, per_col, ind_col = st.columns([2, 2, 3])

    with sel_col:
        selected = st.selectbox("종목 선택", [h["name"] for h in holdings])

    with per_col:
        chart_type = st.radio(
            "차트 유형",
            ["5분", "일", "주", "월", "년"],
            horizontal=True, index=1,
        )

    with ind_col:
        show_ma    = st.checkbox("이동평균선", value=True)
        show_rsi   = st.checkbox("RSI",        value=True)
        show_macd  = st.checkbox("MACD",       value=True)

    TYPE_MAP = {
        "5분": {"period": "1d",  "interval": "5m",  "label": "당일 5분봉"},
        "일":  {"period": "1y",  "interval": "1d",  "label": "일봉 (1년)"},
        "주":  {"period": "1y",  "interval": "1wk", "label": "주봉 (1년)"},
        "월":  {"period": "5y",  "interval": "1mo", "label": "월봉 (5년)"},
        "년":  {"period": "max", "interval": "3mo", "label": "분기봉 (전체)"},
    }

    cfg    = TYPE_MAP[chart_type]
    ticker = next(h["ticker"] for h in holdings if h["name"] == selected)

    if chart_type == "5분":
        st.cache_data.clear()

    hist = get_history(ticker, period=cfg["period"], interval=cfg["interval"])

    if hist.empty:
        msg = ("당일 5분봉 데이터를 불러오지 못했습니다. 장 마감 후이거나 휴장일일 수 있습니다."
               if chart_type == "5분"
               else "차트 데이터를 불러오지 못했습니다.")
        st.warning(msg)
        st.stop()

    if isinstance(hist.columns, pd.MultiIndex):
        hist.columns = hist.columns.get_level_values(0)

    close  = hist["Close"].squeeze()
    open_  = hist["Open"].squeeze()
    high   = hist["High"].squeeze()
    low    = hist["Low"].squeeze()
    volume = hist["Volume"].squeeze()

    # ── 지표 계산 ──────────────────────────────────────
    ma5   = calc_ma(close, 5)
    ma20  = calc_ma(close, 20)
    ma60  = calc_ma(close, 60)
    ma120 = calc_ma(close, 120)
    rsi   = calc_rsi(close, 14)
    rsi_signal = rsi.rolling(6).mean()
    macd_line, macd_signal, macd_hist = calc_macd(close)

    # 전일 고가·저가
    prev_high = float(high.iloc[-2]) if len(high) >= 2 else None
    prev_low  = float(low.iloc[-2])  if len(low)  >= 2 else None
    cur_close = float(close.iloc[-1])

    # ── 서브플롯 구성 ──────────────────────────────────
    n_rows     = 1 + (1) + (1 if show_rsi else 0) + (1 if show_macd else 0)
    row_heights = [0.50, 0.15]
    subplot_titles = [f"{selected}  —  {cfg['label']}", "거래량"]
    if show_rsi:
        row_heights.append(0.17)
        subplot_titles.append("RSI (14)")
    if show_macd:
        row_heights.append(0.18)
        subplot_titles.append("MACD (12,26,9)")

    fig = make_subplots(
        rows=n_rows, cols=1,
        shared_xaxes=True,
        row_heights=row_heights,
        vertical_spacing=0.02,
        subplot_titles=subplot_titles,
    )

    # ── 캔들스틱 ───────────────────────────────────────
    fig.add_trace(go.Candlestick(
        x=hist.index,
        open=open_, high=high, low=low, close=close,
        increasing_line_color="#e24b4a",
        decreasing_line_color="#378add",
        increasing_fillcolor="#e24b4a",
        decreasing_fillcolor="#378add",
        name="가격",
        showlegend=False,
    ), row=1, col=1)

    # ── 이동평균선 ─────────────────────────────────────
    if show_ma:
        MA_CONFIG = [
            (ma5,   "MA5",   "#e24b4a", 1.2),
            (ma20,  "MA20",  "#9b59b6", 1.2),
            (ma60,  "MA60",  "#2ecc71", 1.2),
            (ma120, "MA120", "#e67e22", 1.2),
        ]
        for ma_series, ma_name, ma_color, ma_width in MA_CONFIG:
            fig.add_trace(go.Scatter(
                x=hist.index, y=ma_series,
                mode="lines",
                line=dict(color=ma_color, width=ma_width),
                name=ma_name,
                hovertemplate=f"{ma_name}: %{{y:,.2f}}<extra></extra>",
            ), row=1, col=1)

    # ── 현재가 수평선 ──────────────────────────────────
    fig.add_hline(
        y=cur_close, line_dash="dot",
        line_color="#ffffff" if cur_close else "#aaa",
        line_width=1, opacity=0.6,
        row=1, col=1,
    )

    # ── 전일 고가·저가 ─────────────────────────────────
    if prev_high:
        fig.add_hline(
            y=prev_high, line_dash="dash",
            line_color="#ff9999", line_width=1, opacity=0.7,
            annotation_text="전일고가",
            annotation_position="right",
            annotation_font=dict(size=10, color="#ff9999"),
            row=1, col=1,
        )
    if prev_low:
        fig.add_hline(
            y=prev_low, line_dash="dash",
            line_color="#99bbee", line_width=1, opacity=0.7,
            annotation_text="전일저가",
            annotation_position="right",
            annotation_font=dict(size=10, color="#99bbee"),
            row=1, col=1,
        )

    # ── 거래량 (상승=빨강, 하락=파랑) ──────────────────
    vol_colors = [
        "#e24b4a" if float(c) >= float(o) else "#378add"
        for c, o in zip(close, open_)
    ]
    fig.add_trace(go.Bar(
        x=hist.index, y=volume,
        marker_color=vol_colors,
        name="거래량",
        showlegend=False,
        hovertemplate="거래량: %{y:,.0f}<extra></extra>",
    ), row=2, col=1)

    current_row = 3

    # ── RSI ────────────────────────────────────────────
    if show_rsi:
        fig.add_trace(go.Scatter(
            x=hist.index, y=rsi,
            mode="lines",
            line=dict(color="#9b59b6", width=1.2),
            name="RSI(14)",
            hovertemplate="RSI: %{y:.1f}<extra></extra>",
        ), row=current_row, col=1)
        fig.add_trace(go.Scatter(
            x=hist.index, y=rsi_signal,
            mode="lines",
            line=dict(color="#378add", width=1),
            name="Signal(6)",
            hovertemplate="Signal: %{y:.1f}<extra></extra>",
        ), row=current_row, col=1)
        # 과매수·과매도 기준선
        for level, color in [(70, "rgba(226,75,74,0.3)"), (30, "rgba(55,138,221,0.3)")]:
            fig.add_hline(y=level, line_dash="dot",
                          line_color=color, line_width=1,
                          row=current_row, col=1)
        fig.update_yaxes(range=[0, 100], row=current_row, col=1)
        current_row += 1

    # ── MACD ───────────────────────────────────────────
    if show_macd:
        hist_colors = [
            "#e24b4a" if v >= 0 else "#378add"
            for v in macd_hist.fillna(0)
        ]
        fig.add_trace(go.Bar(
            x=hist.index, y=macd_hist,
            marker_color=hist_colors,
            name="Histogram",
            showlegend=False,
            hovertemplate="Histogram: %{y:.2f}<extra></extra>",
        ), row=current_row, col=1)
        fig.add_trace(go.Scatter(
            x=hist.index, y=macd_line,
            mode="lines",
            line=dict(color="#e24b4a", width=1.2),
            name="MACD(12,26)",
            hovertemplate="MACD: %{y:.2f}<extra></extra>",
        ), row=current_row, col=1)
        fig.add_trace(go.Scatter(
            x=hist.index, y=macd_signal,
            mode="lines",
            line=dict(color="#9b59b6", width=1),
            name="Signal(9)",
            hovertemplate="Signal: %{y:.2f}<extra></extra>",
        ), row=current_row, col=1)
        fig.add_hline(y=0, line_dash="dot",
                      line_color="rgba(150,150,150,0.4)", line_width=1,
                      row=current_row, col=1)

    # ── 레이아웃 ───────────────────────────────────────
    rangebreaks = []
    if chart_type != "5분":
        rangebreaks = [
            dict(bounds=["sat", "mon"]),
            dict(values=KR_HOLIDAYS),
        ]

    total_height = 400 + (150 if show_rsi else 0) + (160 if show_macd else 0)

    fig.update_layout(
        xaxis_rangeslider_visible=False,
        height=total_height,
        margin=dict(t=30, b=20, l=60, r=80),
        hovermode="x unified",
        legend=dict(
            orientation="h",
            x=0, y=1.02,
            font=dict(size=11),
            bgcolor="rgba(0,0,0,0)",
        ),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_xaxes(rangebreaks=rangebreaks, showgrid=True,
                     gridcolor="rgba(150,150,150,0.1)")
    fig.update_yaxes(showgrid=True, gridcolor="rgba(150,150,150,0.1)")

    if chart_type == "5분":
        fig.update_xaxes(tickformat="%H:%M")

    st.plotly_chart(fig, use_container_width=True)

    # ── 기간 통계 ──────────────────────────────────────
    st.markdown("---")
    try:
        close_first = float(open_.iloc[0]) if chart_type == "5분" else float(close.iloc[0])
        period_ret  = (cur_close - close_first) / close_first * 100

        label_ret = "당일 등락률" if chart_type == "5분" else "기간 수익률"
        s1, s2, s3, s4, s5 = st.columns(5)
        s1.metric("현재가",    f"{cur_close:,.2f}")
        s2.metric("기간 고가", f"{float(high.max()):,.2f}")
        s3.metric("기간 저가", f"{float(low.min()):,.2f}")
        s4.metric(label_ret,   f"{period_ret:+.2f}%",
                  delta_color="normal" if period_ret >= 0 else "inverse")
        if not rsi.empty and not pd.isna(rsi.iloc[-1]):
            rsi_val   = float(rsi.iloc[-1])
            rsi_label = "과매수" if rsi_val >= 70 else ("과매도" if rsi_val <= 30 else "중립")
            s5.metric(f"RSI ({rsi_label})", f"{rsi_val:.1f}")
    except Exception:
        pass
