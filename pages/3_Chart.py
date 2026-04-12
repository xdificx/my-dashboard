import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from services.data_service import get_history, get_ticker_data
from services.db_service import get_all_holdings, get_watchlist, add_watchlist, delete_watchlist
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(
    page_title="Chart",
    page_icon="📈",
    layout="wide",
)

with st.sidebar:
    st.markdown("### 차트 설정")

    st.markdown("**차트 유형**")
    chart_type = st.radio(
        "차트 유형",
        ["5분", "일", "주", "월", "년"],
        index=1,
        key="chart_type",
        label_visibility="collapsed",
    )

    st.divider()

    st.markdown("**보조 지표**")
    show_ma   = st.checkbox("이동평균선 (MA5·20·60·120)", value=True,  key="show_ma")
    show_rsi  = st.checkbox("RSI (14)",                   value=True,  key="show_rsi")
    show_macd = st.checkbox("MACD (12,26,9)",             value=False, key="show_macd")

    st.divider()
    st.caption(f"갱신 시각\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

st.markdown("""
<div style="padding:8px 0 4px 0;">
  <span style="font-size:28px;font-weight:800;">📈 Chart</span>
</div>
<div style="font-size:12px;color:#888;margin-bottom:8px;">
  종목 검색 · 캔들차트 · 이동평균선 · RSI · MACD
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════
#  지표 계산
# ══════════════════════════════════════════════════
def calc_ma(series, window):
    return series.rolling(window=window).mean()

def calc_rsi(series, period=14):
    delta    = series.diff()
    gain     = delta.clip(lower=0)
    loss     = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calc_macd(series, fast=12, slow=26, signal=9):
    ema_fast    = series.ewm(span=fast,   adjust=False).mean()
    ema_slow    = series.ewm(span=slow,   adjust=False).mean()
    macd_line   = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line, macd_line - signal_line

# ══════════════════════════════════════════════════
#  공휴일
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
#  종목 선택 영역
# ══════════════════════════════════════════════════
holdings  = get_all_holdings()
watchlist = get_watchlist()

# 티커 입력 힌트
st.markdown("""
<div style="font-size:12px;color:#888;margin-bottom:4px;">
  💡 티커 입력 예시 &nbsp;|&nbsp;
  국내: <b>005930.KS</b> (코스피) &nbsp; <b>035720.KQ</b> (코스닥) &nbsp;|&nbsp;
  해외: <b>AAPL</b> &nbsp; <b>TSLA</b> &nbsp; <b>QQQ</b>
</div>
""", unsafe_allow_html=True)

search_col, name_col, add_col = st.columns([2, 2, 1])

with search_col:
    search_ticker = st.text_input(
        "종목 검색 (티커 직접 입력)",
        placeholder="005930.KS  /  AAPL",
        key="search_ticker",
        label_visibility="collapsed",
    )

with name_col:
    search_name = st.text_input(
        "종목명 (즐겨찾기 저장 시 사용)",
        placeholder="종목명 (예: 삼성전자)",
        key="search_name",
        label_visibility="collapsed",
    )

with add_col:
    if st.button("⭐ 즐겨찾기 추가", use_container_width=True):
        if search_ticker and search_name:
            add_watchlist(search_ticker.strip(), search_name.strip())
            st.success("즐겨찾기 추가됨")
            st.rerun()
        else:
            st.warning("티커와 종목명을 입력하세요.")

# 빠른 선택 버튼 (보유 종목 + 즐겨찾기)
quick_items = []
if holdings:
    quick_items += [{"ticker": h["ticker"], "name": h["name"], "tag": "보유"}
                    for h in holdings]
if watchlist:
    held_tickers = {h["ticker"] for h in holdings}
    quick_items += [{"ticker": w["ticker"], "name": w["name"], "tag": "⭐",
                     "id": w["id"]}
                    for w in watchlist if w["ticker"] not in held_tickers]

if quick_items:
    st.markdown("<div style='font-size:12px;color:#888;margin:6px 0 4px;'>빠른 선택</div>",
                unsafe_allow_html=True)
    btn_cols = st.columns(min(len(quick_items), 8))
    for i, item in enumerate(quick_items[:8]):
        with btn_cols[i % 8]:
            label = f"{'📦' if item['tag']=='보유' else '⭐'} {item['name']}"
            if st.button(label, key=f"quick_{i}", use_container_width=True):
                st.session_state["search_ticker"] = item["ticker"]
                st.session_state["search_name"]   = item["name"]
                st.rerun()

# 즐겨찾기 삭제
if watchlist:
    with st.expander("즐겨찾기 관리"):
        for w in watchlist:
            c1, c2 = st.columns([4, 1])
            c1.markdown(f"⭐ **{w['name']}** `{w['ticker']}`")
            if c2.button("삭제", key=f"del_watch_{w['id']}"):
                delete_watchlist(w["id"])
                st.rerun()

# ── 조회할 티커 결정 ───────────────────────────────
ticker_to_show = search_ticker.strip() if search_ticker.strip() else None

if not ticker_to_show:
    st.info("위 검색창에 티커를 입력하거나 빠른 선택 버튼을 눌러주세요.")
    st.stop()

st.divider()

# ── TYPE_MAP ───────────────────────────────────────
TYPE_MAP = {
    "5분": {"period": "1d",  "interval": "5m",  "label": "당일 5분봉"},
    "일":  {"period": "1y",  "interval": "1d",  "label": "일봉 (1년)"},
    "주":  {"period": "1y",  "interval": "1wk", "label": "주봉 (1년)"},
    "월":  {"period": "5y",  "interval": "1mo", "label": "월봉 (5년)"},
    "년":  {"period": "max", "interval": "3mo", "label": "분기봉 (전체)"},
}
cfg = TYPE_MAP[chart_type]

if chart_type == "5분":
    st.cache_data.clear()

# ── 현재가 정보 헤더 ───────────────────────────────
price_data = get_ticker_data(ticker_to_show)
display_name = search_name.strip() if search_name.strip() else ticker_to_show

if price_data.get("ok"):
    up    = price_data["chg"] >= 0
    color = "#e24b4a" if up else "#378add"
    arrow = "▲" if up else "▼"
    diff  = price_data["price"] * abs(price_data["chg"]) / 100
    st.markdown(f"""
<div style="display:inline-flex;align-items:center;gap:24px;
            background:#f9f9f9;border:1.5px solid #e0e0e0;
            border-radius:12px;padding:14px 24px;margin-bottom:12px;">
  <div>
    <div style="font-size:18px;font-weight:800;color:#111;">{display_name}</div>
    <div style="font-size:12px;color:#888;margin-top:2px;">{ticker_to_show}</div>
  </div>
  <div style="width:1px;height:36px;background:#ddd;"></div>
  <div>
    <div style="font-size:28px;font-weight:700;color:#111;">
      {price_data['price']:,.2f}
    </div>
  </div>
  <div style="display:flex;flex-direction:column;gap:2px;">
    <div style="font-size:14px;font-weight:600;color:{color};">
      {arrow} {diff:,.2f}
    </div>
    <div style="font-size:14px;font-weight:600;color:{color};">
      {arrow} {abs(price_data['chg']):.2f}%
    </div>
  </div>
</div>
""", unsafe_allow_html=True)
else:
    st.markdown(f"""
<div style="display:inline-flex;align-items:center;gap:16px;
            background:#f9f9f9;border:1.5px solid #e0e0e0;
            border-radius:12px;padding:14px 24px;margin-bottom:12px;">
  <div>
    <div style="font-size:18px;font-weight:800;color:#111;">{display_name}</div>
    <div style="font-size:12px;color:#888;">{ticker_to_show}</div>
  </div>
  <div style="font-size:14px;color:#aaa;">현재가 조회 실패</div>
</div>
""", unsafe_allow_html=True)

# ── 데이터 로드 ────────────────────────────────────
with st.spinner("차트 데이터 불러오는 중..."):
    hist = get_history(ticker_to_show, period=cfg["period"], interval=cfg["interval"])

if hist.empty:
    st.warning("데이터를 불러오지 못했습니다. 티커를 확인해주세요.")
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
rsi        = calc_rsi(close, 14)
rsi_signal = rsi.rolling(6).mean()
macd_line, macd_signal, macd_hist = calc_macd(close)

prev_high = float(high.iloc[-2]) if len(high) >= 2 else None
prev_low  = float(low.iloc[-2])  if len(low)  >= 2 else None
cur_close = float(close.iloc[-1])

# ── 서브플롯 구성 ──────────────────────────────────
n_rows      = 2 + (1 if show_rsi else 0) + (1 if show_macd else 0)
row_heights = [0.52, 0.15]
titles      = [f"{display_name}  ({cfg['label']})", "거래량"]
if show_rsi:
    row_heights.append(0.17)
    titles.append("RSI (14)")
if show_macd:
    row_heights.append(0.16)
    titles.append("MACD (12,26,9)")

fig = make_subplots(
    rows=n_rows, cols=1,
    shared_xaxes=True,
    row_heights=row_heights,
    vertical_spacing=0.02,
    subplot_titles=titles,
)

# 캔들스틱
fig.add_trace(go.Candlestick(
    x=hist.index,
    open=open_, high=high, low=low, close=close,
    increasing_line_color="#e24b4a",
    decreasing_line_color="#378add",
    increasing_fillcolor="#e24b4a",
    decreasing_fillcolor="#378add",
    name="가격", showlegend=False,
), row=1, col=1)

# 이동평균선
if show_ma:
    for ma_s, ma_n, ma_c in [
        (ma5,   "MA5",   "#e24b4a"),
        (ma20,  "MA20",  "#9b59b6"),
        (ma60,  "MA60",  "#2ecc71"),
        (ma120, "MA120", "#e67e22"),
    ]:
        fig.add_trace(go.Scatter(
            x=hist.index, y=ma_s, mode="lines",
            line=dict(color=ma_c, width=1.2),
            name=ma_n,
            hovertemplate=f"{ma_n}: %{{y:,.2f}}<extra></extra>",
        ), row=1, col=1)

# 현재가·전일 고저 기준선
fig.add_hline(y=cur_close, line_dash="dot",
              line_color="rgba(200,200,200,0.6)", line_width=1, row=1, col=1)
if prev_high:
    fig.add_hline(y=prev_high, line_dash="dash",
                  line_color="rgba(255,153,153,0.7)", line_width=1,
                  annotation_text="전일고가",
                  annotation_font=dict(size=10, color="#ff9999"),
                  annotation_position="right", row=1, col=1)
if prev_low:
    fig.add_hline(y=prev_low, line_dash="dash",
                  line_color="rgba(153,187,238,0.7)", line_width=1,
                  annotation_text="전일저가",
                  annotation_font=dict(size=10, color="#99bbee"),
                  annotation_position="right", row=1, col=1)

# 거래량 (상승=빨강, 하락=파랑)
vol_colors = ["#e24b4a" if float(c) >= float(o) else "#378add"
              for c, o in zip(close, open_)]
fig.add_trace(go.Bar(
    x=hist.index, y=volume, marker_color=vol_colors,
    name="거래량", showlegend=False,
    hovertemplate="거래량: %{y:,.0f}<extra></extra>",
), row=2, col=1)

cur_row = 3

# RSI
if show_rsi:
    fig.add_trace(go.Scatter(
        x=hist.index, y=rsi, mode="lines",
        line=dict(color="#9b59b6", width=1.2), name="RSI(14)",
        hovertemplate="RSI: %{y:.1f}<extra></extra>",
    ), row=cur_row, col=1)
    fig.add_trace(go.Scatter(
        x=hist.index, y=rsi_signal, mode="lines",
        line=dict(color="#378add", width=1), name="Signal(6)",
        hovertemplate="Signal: %{y:.1f}<extra></extra>",
    ), row=cur_row, col=1)
    for lvl, clr in [(70, "rgba(226,75,74,0.25)"), (30, "rgba(55,138,221,0.25)")]:
        fig.add_hline(y=lvl, line_dash="dot", line_color=clr,
                      line_width=1, row=cur_row, col=1)
    fig.update_yaxes(range=[0, 100], row=cur_row, col=1)
    cur_row += 1

# MACD
if show_macd:
    h_colors = ["#e24b4a" if v >= 0 else "#378add"
                for v in macd_hist.fillna(0)]
    fig.add_trace(go.Bar(
        x=hist.index, y=macd_hist, marker_color=h_colors,
        name="Histogram", showlegend=False,
        hovertemplate="Histogram: %{y:.2f}<extra></extra>",
    ), row=cur_row, col=1)
    fig.add_trace(go.Scatter(
        x=hist.index, y=macd_line, mode="lines",
        line=dict(color="#e24b4a", width=1.2), name="MACD(12,26)",
        hovertemplate="MACD: %{y:.2f}<extra></extra>",
    ), row=cur_row, col=1)
    fig.add_trace(go.Scatter(
        x=hist.index, y=macd_signal, mode="lines",
        line=dict(color="#9b59b6", width=1), name="Signal(9)",
        hovertemplate="Signal: %{y:.2f}<extra></extra>",
    ), row=cur_row, col=1)
    fig.add_hline(y=0, line_dash="dot",
                  line_color="rgba(150,150,150,0.3)", line_width=1,
                  row=cur_row, col=1)

# 레이아웃
rangebreaks = []
if chart_type != "5분":
    rangebreaks = [dict(bounds=["sat","mon"]), dict(values=KR_HOLIDAYS)]

total_height = 420 + (150 if show_rsi else 0) + (150 if show_macd else 0)

fig.update_layout(
    xaxis_rangeslider_visible=False,
    height=total_height,
    margin=dict(t=30, b=20, l=60, r=80),
    hovermode="x unified",
    legend=dict(orientation="h", x=0, y=1.02,
                font=dict(size=11), bgcolor="rgba(0,0,0,0)"),
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
)
fig.update_xaxes(rangebreaks=rangebreaks,
                 showgrid=True, gridcolor="rgba(150,150,150,0.1)")
fig.update_yaxes(showgrid=True, gridcolor="rgba(150,150,150,0.1)")
if chart_type == "5분":
    fig.update_xaxes(tickformat="%H:%M")

st.plotly_chart(fig, use_container_width=True)

# ── 기간 통계 ──────────────────────────────────────
st.markdown("---")
try:
    close_first = float(open_.iloc[0]) if chart_type == "5분" else float(close.iloc[0])
    period_ret  = (cur_close - close_first) / close_first * 100
    label_ret   = "당일 등락률" if chart_type == "5분" else "기간 수익률"

    s1, s2, s3, s4, s5 = st.columns(5)
    s1.metric("현재가",    f"{cur_close:,.2f}")
    s2.metric("기간 고가", f"{float(high.max()):,.2f}")
    s3.metric("기간 저가", f"{float(low.min()):,.2f}")
    s4.metric(label_ret,   f"{period_ret:+.2f}%",
              delta_color="normal" if period_ret >= 0 else "inverse")
    if not rsi.empty and not pd.isna(rsi.iloc[-1]):
        rv    = float(rsi.iloc[-1])
        rlabel = "과매수" if rv >= 70 else ("과매도" if rv <= 30 else "중립")
        s5.metric(f"RSI({rlabel})", f"{rv:.1f}")
except Exception:
    pass
