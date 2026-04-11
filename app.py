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
        """<div style="position:fixed;bottom:20px;left:0;width:18rem;
                       padding:0 1.5rem;box-sizing:border-box;
                       font-size:13px;color:#888;line-height:1.8;">
        📡 데이터: Yahoo Finance<br>
        ⏱ 15분 지연<br>
        🕐 갱신: {now}
        </div>""".format(now=__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')),
        unsafe_allow_html=True
    )

fx = fetch("USDKRW=X", "원/달러 환율")
FX = fx["price"] if fx.get("ok") else 1330.0

# ══════════════════════════════════════════════════
#  종목 분류 함수 (도넛 차트용)
# ══════════════════════════════════════════════════
# 국내 ETF 티커 목록 (코스피/코스닥 상장 ETF 앞 3자리 기준)
KR_ETF_PREFIXES = ("069","091","102","114","122","132","139","148","152","157",
                   "160","168","176","182","183","192","195","200","202","203",
                   "208","209","214","215","217","219","226","228","229","233",
                   "236","238","251","252","253","261","266","267","269","272",
                   "273","276","278","279","280","282","284","287","289","290",
                   "292","294","295","296","298","299","300","304","305","306",
                   "308","310","314","315","316","317","319","321","322","323",
                   "329","332","333","334","336","337","338","339","340","341",
                   "343","346","352","357","360","361","364","365","367","371",
                   "372","373","374","375","376","377","379","381","385","387",
                   "388","389","390","391","392","394","395","396","397","398",
                   "400","401","402","403","404","405","406","407","408","409",
                   "411","412","413","415","416","417","418","420","421","422",
                   "424","425","426","427","428","429","430","432","433","434",
                   "436","437","438","439","440","441","442","443","444","445",
                   "447","448","449","450","451","452","453","454","456","457",
                   "458","459","460","461","462","463","465","466","467","468",
                   "469","470","471","472","473","474","475","476","477","478",
                   "479","480","481","482","483","484","485","486","487","488",
                   "489","490","491","492","493","494","495","496","497","498",
                   "499","500")

# 해외 ETF 티커 목록 (대표적인 것들)
US_ETF_TICKERS = {
    "SPY","QQQ","IVV","VOO","VTI","VEA","VWO","EEM","GLD","IAU",
    "SLV","USO","TLT","IEF","LQD","HYG","VNQ","XLF","XLK","XLE",
    "XLV","XLI","XLY","XLP","XLU","XLB","XLRE","ARKK","ARKG","ARKW",
    "SCHD","VYM","DVY","SDY","HDV","DGRO","VIG","NOBL","JEPI","JEPQ",
    "QYLD","RYLD","XYLD","TQQQ","SOXL","FNGU","TECL","SPXL","UPRO",
    "SQQQ","SDOW","UVXY","VXX","BITO","IBIT","FBTC","GBTC","ETHE",
    "AGG","BND","BNDX","EMB","JNK","VCIT","VCSH","BSV","BIV","BLV",
    "VGK","EWJ","EWZ","EWC","EWA","EWG","EWU","EWI","EWS","EWT",
    "EWY","EWH","EWM","EWP","EWQ","EWD","EWN","EWO","EWL","EWK",
    "ACWI","URTH","IOO","VT","IXUS","VXUS","EFA","SCZ","VSS",
    "DIA","MDY","IJH","IJR","VBR","VBK","VTV","VUG","IWM","IWD","IWF",
}

def classify_holding(h: dict) -> str:
    """보유 종목을 4개 카테고리로 분류"""
    ticker = h["ticker"].upper()
    market = h.get("market", "KR")

    if market == "KR" or ticker.endswith(".KS") or ticker.endswith(".KQ"):
        code = ticker.replace(".KS","").replace(".KQ","")
        if code[:3] in KR_ETF_PREFIXES:
            return "국내 ETF"
        return "국내 개별 종목"
    else:
        base = ticker.split(".")[0]
        if base in US_ETF_TICKERS:
            return "해외 ETF"
        return "해외 개별 종목"

# ══════════════════════════════════════════════════
#  섹션 1 — Market Indicator + 도넛 차트 (같은 행)
# ══════════════════════════════════════════════════
left_col, right_col = st.columns([3, 2], gap="medium")

with left_col:
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

with right_col:
    st.markdown("### 🥧 자산 배분")
    holdings_for_donut = get_all_holdings()

    if not holdings_for_donut:
        st.info("Portfolio 페이지에서 종목을 추가하면 자산 배분 차트가 표시됩니다.")
    else:
        # 카테고리별 투자금액 합산
        category_amounts = {
            "국내 개별 종목": 0,
            "국내 ETF": 0,
            "해외 개별 종목": 0,
            "해외 ETF": 0,
        }
        for h in holdings_for_donut:
            cat = classify_holding(h)
            cost = (round(h["avg"] * FX) if h["market"] == "US" else round(h["avg"])) * h["qty"]
            category_amounts[cat] += cost

        # 0원 카테고리 제외
        labels = [k for k, v in category_amounts.items() if v > 0]
        values = [v for v in category_amounts.values() if v > 0]

        if values:
            DONUT_COLORS = ["#e24b4a", "#ff9999", "#378add", "#99bbee"]
            colors_used  = DONUT_COLORS[:len(labels)]
            total_cost   = sum(values)

            fig_donut = go.Figure(go.Pie(
                labels=labels,
                values=values,
                hole=0.58,
                marker=dict(colors=colors_used, line=dict(color="#fff", width=2)),
                textinfo="percent",
                textfont=dict(size=12),
                hovertemplate="%{label}<br>%{value:,.0f}원<br>%{percent}<extra></extra>",
            ))

            # 도넛 차트 + 우측 카테고리 테이블을 나란히
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
                for label, val, color in zip(labels, values, colors_used):
                    pct = val / total_cost * 100
                    st.markdown(f"""
<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
  <div style="width:12px;height:12px;border-radius:3px;
              background:{color};flex-shrink:0;"></div>
  <div style="font-size:12px;line-height:1.5;">
    <div style="color:#555;font-weight:600;">{label}</div>
    <div style="color:#333;">{val:,.0f}원</div>
    <div style="color:#888;">{pct:.1f}%</div>
  </div>
</div>""", unsafe_allow_html=True)

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
