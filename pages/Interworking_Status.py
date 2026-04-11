import streamlit as st
import yfinance as yf
from datetime import datetime
import traceback
import time

st.set_page_config(
    page_title="Interworking Status",
    page_icon="📡",
    layout="wide",
)

# ══════════════════════════════════════════════════
#  점검 항목 — 전체 yfinance
# ══════════════════════════════════════════════════
CHECK_ITEMS = [
    # 국내 지수
    {"group": "🇰🇷 국내 지수",   "label": "KOSPI",       "ticker": "^KS11"},
    {"group": "🇰🇷 국내 지수",   "label": "KOSDAQ",      "ticker": "^KQ11"},
    {"group": "🇰🇷 국내 지수",   "label": "KOSPI 200",   "ticker": "^KS200"},
    # 국내 종목 (샘플)
    {"group": "🇰🇷 국내 종목",   "label": "삼성전자",     "ticker": "005930.KS"},
    {"group": "🇰🇷 국내 종목",   "label": "카카오",       "ticker": "035720.KQ"},
    {"group": "🇰🇷 국내 종목",   "label": "SK하이닉스",   "ticker": "000660.KS"},
    # 해외 지수
    {"group": "🌎 해외 지수",    "label": "S&P 500",     "ticker": "^GSPC"},
    {"group": "🌎 해외 지수",    "label": "나스닥",       "ticker": "^IXIC"},
    {"group": "🌎 해외 지수",    "label": "다우존스",     "ticker": "^DJI"},
    # 거시 지표
    {"group": "📡 거시 지표",    "label": "달러 인덱스",  "ticker": "DX-Y.NYB"},
    {"group": "📡 거시 지표",    "label": "원/달러 환율", "ticker": "USDKRW=X"},
    {"group": "📡 거시 지표",    "label": "미 10년 국채", "ticker": "^TNX"},
    {"group": "📡 거시 지표",    "label": "금 선물",      "ticker": "GC=F"},
    {"group": "📡 거시 지표",    "label": "WTI 원유",     "ticker": "CL=F"},
]

# ══════════════════════════════════════════════════
#  점검 함수
# ══════════════════════════════════════════════════
@st.cache_data(ttl=300)
def check_ticker(ticker: str) -> tuple[bool, str, str]:
    """(성공여부, 값, 오류메시지)"""
    try:
        info  = yf.Ticker(ticker).fast_info
        price = info.last_price
        if price and price > 0:
            return True, f"{price:,.4f}", ""
        return False, "", "가격 0 또는 None 반환"
    except Exception:
        lines = [l.strip() for l in traceback.format_exc().strip().splitlines() if l.strip()]
        return False, "", " | ".join(lines[-2:])[:300]

# ══════════════════════════════════════════════════
#  사이드바
# ══════════════════════════════════════════════════
with st.sidebar:
    st.divider()
    auto_refresh = st.toggle("5분 자동 갱신", value=False)
    if st.button("🔄 지금 즉시 재점검"):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.caption(f"점검 시각\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ══════════════════════════════════════════════════
#  헤더
# ══════════════════════════════════════════════════
st.title("Interworking Status")
st.caption(
    "모든 데이터: Yahoo Finance (yfinance)  |  "
    "KRX Open API 발급 후 국내 데이터 품질 업그레이드 예정"
)

# ══════════════════════════════════════════════════
#  점검 실행 + 결과 수집
# ══════════════════════════════════════════════════
results = []
for item in CHECK_ITEMS:
    ok, val, err = check_ticker(item["ticker"])
    results.append({**item, "ok": ok, "val": val, "err": err})

# ══════════════════════════════════════════════════
#  전체 요약 배너
# ══════════════════════════════════════════════════
total   = len(results)
failed  = [r for r in results if not r["ok"]]
success = total - len(failed)

if not failed:
    st.success(f"✅ 전체 정상 — {success}/{total}개 항목 모두 연결 성공")
elif len(failed) < total:
    st.warning(f"⚠️ 일부 실패 — {success}/{total}개 연결 성공  |  실패: {len(failed)}개")
else:
    st.error(f"🔴 전체 실패 — {total}개 항목 모두 조회 불가")

st.divider()

# ══════════════════════════════════════════════════
#  그룹별 상세 표시
# ══════════════════════════════════════════════════
groups = {}
for r in results:
    groups.setdefault(r["group"], []).append(r)

for group_name, items in groups.items():
    group_fail = [i for i in items if not i["ok"]]
    status_icon = "✅" if not group_fail else f"❌ {len(group_fail)}개 실패"
    st.subheader(f"{group_name}  {status_icon}")

    cols = st.columns(len(items))
    for col, r in zip(cols, items):
        with col:
            if r["ok"]:
                st.success(f"**{r['label']}**\n\n{r['val']}\n\n`{r['ticker']}`")
            else:
                st.error(f"**{r['label']}**\n\n연결 실패\n\n`{r['ticker']}`")
                if r["err"]:
                    with st.expander("오류 상세"):
                        st.code(r["err"], language=None)

st.divider()

# ══════════════════════════════════════════════════
#  실패 항목 전체 목록 (있을 때만)
# ══════════════════════════════════════════════════
if failed:
    st.subheader("❌ 실패 항목 목록")
    for r in failed:
        st.markdown(
            f"- **{r['group']}** › **{r['label']}** (`{r['ticker']}`)"
            + (f"\n  → `{r['err'][:100]}`" if r["err"] else "")
        )

# ══════════════════════════════════════════════════
#  KRX Open API 업그레이드 안내
# ══════════════════════════════════════════════════
with st.expander("🔧 KRX Open API 연동 예정 항목"):
    st.markdown(
        "KRX Open API 키 발급 후 아래 항목이 공식 KRX 데이터로 업그레이드됩니다.\n\n"
        "- 국내 지수 (KOSPI·KOSDAQ·KOSPI200) — KRX 공식 종가\n"
        "- 국내 개별 종목 현재가 — KRX 공식 데이터 (누락 없음)\n"
        "- PER · PBR · 배당수익률 — 종목별 세부 지표\n"
        "- 외국인 순매수 · 기관 매매 동향\n\n"
        "현재는 yfinance로 대체 조회 중입니다. (15분 지연, 간헐적 누락 가능)"
    )

# ══════════════════════════════════════════════════
#  자동 갱신
# ══════════════════════════════════════════════════
if auto_refresh:
    time.sleep(300)
    st.rerun()
