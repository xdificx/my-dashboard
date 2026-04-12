import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from services.data_service import get_history, get_ticker_data, get_ticker_name, get_stock_info
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
    # 티커 입력 시 종목명 자동 조회
    auto_name = ""
    if search_ticker and search_ticker.strip():
        with st.spinner("종목명 조회 중..."):
            auto_name = get_ticker_name(search_ticker.strip())

    search_name = st.text_input(
        "종목명",
        value=auto_name,
        placeholder="티커 입력 시 자동 조회됩니다",
        key="search_name",
        label_visibility="collapsed",
    )

with add_col:
    if st.button("즐겨찾기 추가", use_container_width=True):
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
    "일":  {"period": "3mo", "interval": "1d",  "label": "일봉 (3개월)"},
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

# 해외 종목 여부 판단 (KS·KQ·KX 없으면 해외)
is_foreign = not any(ticker_to_show.upper().endswith(s)
                     for s in [".KS", ".KQ", ".KX"])

# 환율 조회
fx_info = get_ticker_data("USDKRW=X")
FX_RATE = fx_info["price"] if fx_info.get("ok") else 1330.0

# 세부정보 병렬 조회
with st.spinner("종목 정보 불러오는 중..."):
    stock_info = get_stock_info(ticker_to_show)

# ── 종목 카드 + 세부정보 카드 나란히 ──────────────
info_left, info_right = st.columns([2, 3], gap="medium")

with info_left:
    if price_data.get("ok"):
        up    = price_data["chg"] >= 0
        color = "#e24b4a" if up else "#378add"
        arrow = "▲" if up else "▼"
        diff  = price_data["price"] * abs(price_data["chg"]) / 100
        krw_html = ""
        if is_foreign:
            krw_price = price_data["price"] * FX_RATE
            krw_diff  = diff * FX_RATE
            krw_html  = (
                f'<div style="font-size:12px;color:#888;margin-top:6px;">'
                f'≈ {krw_price:,.0f}원 '
                f'<span style="color:{color};">{arrow} {krw_diff:,.0f}원</span>'
                f'<span style="font-size:11px;"> (1 USD = {FX_RATE:,.2f} KRW)</span>'
                f'</div>'
            )
        exch = f' &nbsp;·&nbsp; {stock_info["거래소"]}' if stock_info.get("거래소") else ''
        curr = f' &nbsp;·&nbsp; {stock_info["통화"]}' if stock_info.get("통화") else ''
        sect = f'<div style="font-size:11px;color:#aaa;margin-top:2px;">{stock_info["섹터"]}</div>' if stock_info.get("섹터") else ''
        st.markdown(f"""
<div style="background:#f9f9f9;border:1.5px solid #e0e0e0;
            border-radius:12px;padding:16px 20px;margin-bottom:12px;height:100%;">
  <div style="display:flex;align-items:center;gap:20px;">
    <div>
      <div style="font-size:18px;font-weight:800;color:#111;">{display_name}</div>
      <div style="font-size:12px;color:#888;margin-top:2px;">{ticker_to_show}{exch}{curr}</div>
      {sect}
    </div>
    <div style="width:1px;height:40px;background:#ddd;flex-shrink:0;"></div>
    <div>
      <div style="font-size:26px;font-weight:700;color:#111;">{price_data['price']:,.2f}</div>
      <div style="font-size:13px;font-weight:600;color:{color};margin-top:2px;">
        {arrow} {diff:,.2f} &nbsp; {arrow} {abs(price_data['chg']):.2f}%
      </div>
    </div>
  </div>
  {krw_html}
</div>
""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
<div style="background:#f9f9f9;border:1.5px solid #e0e0e0;
            border-radius:12px;padding:16px 20px;margin-bottom:12px;">
  <div style="font-size:18px;font-weight:800;color:#111;">{display_name}</div>
  <div style="font-size:12px;color:#888;">{ticker_to_show}</div>
  <div style="font-size:13px;color:#aaa;margin-top:8px;">현재가 조회 실패</div>
</div>
""", unsafe_allow_html=True)

with info_right:
    if stock_info:
        groups = [
            ("기업 규모",    ["시가총액", "발행주식수", "유동주식수", "평균거래량"]),
            ("밸류에이션",   ["PER", "PBR", "EPS", "배당수익률", "베타(1Y)"]),
            ("52주 범위",    ["52주 최고", "52주 최저"]),
        ]
        items_html = ""
        for group_title, keys in groups:
            row_items = [(k, stock_info[k]) for k in keys if stock_info.get(k)]
            if not row_items:
                continue
            items_html += (
                f'<div style="font-size:11px;color:#aaa;font-weight:600;'
                f'margin:8px 0 4px 0;letter-spacing:0.5px;">{group_title}</div>'
                f'<div style="display:flex;flex-wrap:wrap;gap:6px;">'
            )
            for k, v in row_items:
                items_html += (
                    f'<div style="background:#fff;border:1px solid #e8e8e8;'
                    f'border-radius:8px;padding:5px 10px;font-size:12px;">'
                    f'<span style="color:#888;">{k}</span>'
                    f'<span style="font-weight:700;color:#111;margin-left:6px;">{v}</span>'
                    f'</div>'
                )
            items_html += "</div>"
        st.markdown(
            f'<div style="background:#f9f9f9;border:1.5px solid #e0e0e0;'
            f'border-radius:12px;padding:14px 16px;margin-bottom:12px;">'
            f'{items_html}'
            f'</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<div style="background:#f9f9f9;border:1.5px solid #e0e0e0;'
            'border-radius:12px;padding:14px 16px;margin-bottom:12px;'
            'font-size:13px;color:#aaa;">세부정보 조회 실패</div>',
            unsafe_allow_html=True
        )


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

from datetime import date, timedelta
import yfinance as yf

# ── 자동 통계 계산 ──────────────────────────────
try:
    close_first = float(open_.iloc[0]) if chart_type == "5분" else float(close.iloc[0])
    auto_ret    = (cur_close - close_first) / close_first * 100
    auto_high   = float(high.max())
    auto_low    = float(low.min())
except Exception:
    auto_ret = auto_high = auto_low = None

# ── 세션 초기화 (최초 1회) ────────────────────
_defs = {
    "val_high": None, "val_low": None, "val_ret": None,
    "tag_high": "",   "tag_low": "",   "tag_ret": "",
}
for k, v in _defs.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── 차트(좌 70%) + 지표 패널(우 30%) ─────────
chart_col, panel_col = st.columns([7, 3], gap="small")

with chart_col:
    st.plotly_chart(fig, use_container_width=True)

with panel_col:
    # 값: 세션에 저장된 커스텀 값 우선, 없으면 자동
    disp_high = st.session_state["val_high"] if st.session_state["val_high"] is not None else auto_high
    disp_low  = st.session_state["val_low"]  if st.session_state["val_low"]  is not None else auto_low
    disp_ret  = st.session_state["val_ret"]  if st.session_state["val_ret"]  is not None else auto_ret

    def mini_card(label, value, tag, fmt, color):
        period_label = tag if tag else f"{chart_type}봉 전체"
        if value is not None:
            if fmt == "ret":
                up  = value >= 0
                clr = "#e24b4a" if up else "#378add"
                arr = "▲" if up else "▼"
                val_html = f'<b style="font-size:20px;color:{clr};">{arr} {abs(value):.2f}%</b>'
            else:
                val_html = f'<b style="font-size:20px;color:{color};">{value:,.2f}</b>'
        else:
            val_html = '<span style="color:#aaa;">—</span>'

        return (
            f'<div style="background:#f9f9f9;border:1px solid #e0e0e0;'
            f'border-radius:10px;padding:8px 12px 10px 12px;margin-bottom:4px;">'
            f'<div style="font-size:11px;color:#888;font-weight:600;margin-bottom:3px;">{label}</div>'
            f'{val_html}'
            f'<div style="font-size:10px;color:#aaa;margin-top:3px;">{period_label}</div>'
            f'</div>'
        )

    st.markdown(
        mini_card("기간 고가",   disp_high, st.session_state["tag_high"], "price", "#e24b4a") +
        mini_card("기간 저가",   disp_low,  st.session_state["tag_low"],  "price", "#378add") +
        mini_card("기간 수익률", disp_ret,  st.session_state["tag_ret"],  "ret",   ""),
        unsafe_allow_html=True
    )

    # RSI 카드
    if not rsi.empty and not pd.isna(rsi.iloc[-1]):
        rv     = float(rsi.iloc[-1])
        rlabel = "과매수" if rv >= 70 else ("과매도" if rv <= 30 else "중립")
        rcolor = "#e24b4a" if rv >= 70 else ("#378add" if rv <= 30 else "#555")
        rbg    = "rgba(226,75,74,0.06)" if rv >= 70 else ("rgba(55,138,221,0.06)" if rv <= 30 else "#f9f9f9")
        rbar   = min(int(rv), 100)
        st.markdown(f"""
<div style="background:{rbg};border:1px solid #e0e0e0;border-radius:10px;
            padding:8px 12px 10px 12px;margin-top:4px;">
  <div style="font-size:11px;color:#888;font-weight:600;margin-bottom:4px;">RSI (14)</div>
  <div style="font-size:20px;font-weight:700;color:{rcolor};">{rv:.1f}</div>
  <div style="font-size:11px;color:{rcolor};">{rlabel} {"(70 이상)" if rv>=70 else ("(30 이하)" if rv<=30 else "(30~70)")}</div>
  <div style="background:#e0e0e0;border-radius:4px;height:4px;margin-top:6px;">
    <div style="background:{rcolor};width:{rbar}%;height:4px;border-radius:4px;"></div>
  </div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════
#  기간 설정 섹션 (차트 아래 별도 배치 — 버튼 클릭 시 차트 재렌더링 없음)
# ══════════════════════════════════════════════════
st.markdown("---")
st.markdown("#### 기간 직접 설정")
st.caption("기간을 지정하면 위 카드의 값이 해당 기간 기준으로 업데이트됩니다.")

g1, g2, g3 = st.columns(3, gap="medium")

def period_form(col, title, val_key, tag_key, color):
    with col:
        with st.container(border=True):
            st.markdown(f"**{title}**")
            mode = st.radio(
                "기간 선택",
                ["자동 (차트 기간)", "직접 설정"],
                key=f"mode_{val_key}",
                label_visibility="collapsed",
            )
            if mode == "직접 설정":
                saved_start = st.session_state.get(f"cs_{val_key}", date.today() - timedelta(days=90))
                saved_end   = st.session_state.get(f"ce_{val_key}", date.today())
                c1, c2 = st.columns(2)
                cs = c1.date_input("시작일", value=saved_start, key=f"s_{val_key}")
                ce = c2.date_input("종료일", value=saved_end,   key=f"e_{val_key}")
                if st.button("계산", key=f"calc_{val_key}", use_container_width=True):
                    if cs < ce:
                        with st.spinner("조회 중..."):
                            try:
                                df_c = yf.download(
                                    ticker_to_show,
                                    start=str(cs), end=str(ce),
                                    interval="1d", progress=False
                                )
                                if isinstance(df_c.columns, pd.MultiIndex):
                                    df_c.columns = df_c.columns.get_level_values(0)
                                if not df_c.empty:
                                    if "고가" in title:
                                        st.session_state[val_key] = float(df_c["High"].max())
                                    elif "저가" in title:
                                        st.session_state[val_key] = float(df_c["Low"].min())
                                    else:
                                        o_ = float(df_c["Open"].iloc[0])
                                        c_ = float(df_c["Close"].iloc[-1])
                                        st.session_state[val_key] = (c_ - o_) / o_ * 100
                                    st.session_state[f"cs_{val_key}"] = cs
                                    st.session_state[f"ce_{val_key}"] = ce
                                    st.session_state[tag_key] = f"{cs} ~ {ce}"
                                    st.rerun()
                                else:
                                    st.warning("해당 기간에 데이터가 없습니다.")
                            except Exception as e:
                                st.error(str(e))
                    else:
                        st.warning("시작일이 종료일보다 앞이어야 합니다.")
            else:
                # 자동으로 복귀
                if st.session_state.get(val_key) is not None:
                    st.session_state[val_key] = None
                    st.session_state[tag_key] = ""
                    st.rerun()

period_form(g1, "기간 고가",   "val_high", "tag_high", "#e24b4a")
period_form(g2, "기간 저가",   "val_low",  "tag_low",  "#378add")
period_form(g3, "기간 수익률", "val_ret",  "tag_ret",  "#555")

# ══════════════════════════════════════════════════
#  세부 지표 섹션
# ══════════════════════════════════════════════════
st.markdown("---")
st.markdown("#### 세부 지표")

if not stock_info:
    st.info("세부 지표를 불러오지 못했습니다. 티커를 확인해주세요.")
else:
    # 지표 그룹 정의 + 각 지표별 설명
    INDICATOR_META = {
        "PER":            ("주가수익비율",       "주가 ÷ EPS. 낮을수록 이익 대비 저렴. 업종 평균과 비교 필수."),
        "선행 PER":       ("선행 주가수익비율",   "미래 추정 이익 기준 PER. 현재 PER보다 낮으면 이익 성장 기대."),
        "PBR":            ("주가순자산비율",       "주가 ÷ 순자산. 1 미만이면 자산보다 싸게 거래 중."),
        "PSR":            ("주가매출비율",         "주가 ÷ 매출. 적자 기업 밸류에이션에 활용."),
        "PEG":            ("주가이익성장비율",     "PER ÷ EPS성장률. 1 이하면 성장 대비 저평가."),
        "EV/EBITDA":      ("기업가치/상각전이익", "부채 포함 기업가치 ÷ EBITDA. 6~10배가 일반적."),
        "EPS":            ("주당순이익",           "주식 1주당 이익. 꾸준히 성장하는 기업이 핵심."),
        "ROE":            ("자기자본이익률",       "순이익 ÷ 자기자본. 15% 이상이면 우량 기업."),
        "ROA":            ("총자산이익률",         "순이익 ÷ 총자산. 자산 활용 효율성 측정."),
        "영업이익률":     ("영업이익률",           "영업이익 ÷ 매출. 본업 경쟁력을 가장 직접적으로 반영."),
        "순이익률":       ("순이익률",             "순이익 ÷ 매출. 영업이익률보다 일회성 항목 영향 받음."),
        "매출 성장률":    ("매출 성장률",          "전년 대비 매출 증가율. 성장세 지속 여부 확인."),
        "이익 성장률":    ("이익 성장률",          "전년 대비 이익 증가율. 매출보다 빠르면 수익성 개선 중."),
        "FCF":            ("잉여현금흐름",         "영업현금흐름 − CAPEX. 실제 사용 가능한 현금. 이익보다 신뢰도 높음."),
        "FCF Yield":      ("FCF 수익률",           "FCF ÷ 시가총액. 국채 금리보다 높으면 주식이 매력적."),
        "영업현금흐름":   ("영업현금흐름",         "본업에서 창출한 현금. FCF 계산의 기반."),
        "배당수익률":     ("배당수익률",           "배당금 ÷ 주가. 은행 금리와 비교해 투자 매력도 판단."),
        "배당금(연간)":   ("연간 배당금",          "1주당 연간 배당금. 배당 지속 가능성을 FCF와 함께 확인."),
        "배당성향":       ("배당성향",             "배당금 ÷ 순이익. 70% 이하면 배당 지속 안정적."),
        "5Y 평균배당수익률": ("5년 평균 배당수익률", "최근 5년 평균. 현재 배당수익률과 비교해 고저 판단."),
        "부채비율":       ("부채비율",             "총부채 ÷ 자기자본. 200% 이하가 일반적 안전권."),
        "유동비율":       ("유동비율",             "유동자산 ÷ 유동부채. 1.5 이상이면 단기 지급 능력 양호."),
        "베타(1Y)":       ("베타",                 "시장 대비 변동성. 1 초과면 시장보다 변동 큼, 미만이면 방어적."),
    }

    GROUPS = [
        ("밸류에이션",   ["PER", "선행 PER", "PBR", "PSR", "PEG", "EV/EBITDA", "EPS"]),
        ("수익성",       ["ROE", "ROA", "영업이익률", "순이익률", "매출 성장률", "이익 성장률"]),
        ("현금흐름",     ["FCF", "FCF Yield", "영업현금흐름"]),
        ("배당",         ["배당수익률", "배당금(연간)", "배당성향", "5Y 평균배당수익률"]),
        ("재무 안정성",  ["부채비율", "유동비율", "베타(1Y)"]),
    ]

    for group_title, keys in GROUPS:
        items = [(k, stock_info.get(k)) for k in keys if stock_info.get(k)]
        if not items:
            continue

        st.markdown(f"**{group_title}**")
        cols = st.columns(len(items) if len(items) <= 5 else 5)

        for i, (key, val) in enumerate(items):
            col = cols[i % 5]
            meta_name, meta_desc = INDICATOR_META.get(key, (key, ""))
            # 툴팁 텍스트에서 따옴표 이스케이프
            safe_desc = meta_desc.replace('"', '&quot;').replace("'", '&#39;')
            with col:
                st.markdown(f"""
<div style="background:#f9f9f9;border:1px solid #e0e0e0;
            border-radius:10px;padding:10px 12px;margin-bottom:8px;
            position:relative;">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;">
    <div style="font-size:11px;color:#888;font-weight:600;">{key}</div>
    <div style="position:relative;display:inline-block;">
      <span style="font-size:13px;color:#bbb;cursor:help;line-height:1;"
            onmouseenter="this.nextElementSibling.style.display='block'"
            onmouseleave="this.nextElementSibling.style.display='none'">&#9432;</span>
      <div style="display:none;position:absolute;right:0;top:20px;
                  background:#333;color:#fff;font-size:11px;
                  padding:6px 10px;border-radius:6px;
                  width:200px;line-height:1.5;z-index:9999;
                  white-space:normal;box-shadow:0 2px 8px rgba(0,0,0,0.2);">
        {safe_desc}
      </div>
    </div>
  </div>
  <div style="font-size:18px;font-weight:700;color:#111;margin-top:3px;">{val}</div>
</div>
""", unsafe_allow_html=True)
        st.markdown("")
st.markdown("")
