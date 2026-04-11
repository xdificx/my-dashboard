import streamlit as st
from services.data_service import get_ticker_data
from services.db_service import get_all_holdings

st.title("📊 Overview")

holdings = get_all_holdings()

fx = get_ticker_data("USDKRW=X")
FX = fx["price"] if fx.get("ok") else 1330

c1, c2, c3 = st.columns(3)

with c1:
    st.subheader("🇰🇷 국내 지수")
    for t, n in [("^KS11", "KOSPI"), ("^KQ11", "KOSDAQ")]:
        d = get_ticker_data(t)
        if d["ok"]:
            st.metric(n, f"{d['price']:,.0f}", f"{d['chg']:+.2f}%")

with c2:
    st.subheader("🌎 해외 지수")
    for t, n in [("^GSPC", "S&P500"), ("^IXIC", "나스닥")]:
        d = get_ticker_data(t)
        if d["ok"]:
            st.metric(n, f"{d['price']:,.0f}", f"{d['chg']:+.2f}%")

with c3:
    st.subheader("📡 매크로")
    for t, n in [("USDKRW=X", "환율"), ("^VIX", "VIX")]:
        d = get_ticker_data(t)
        if d["ok"]:
            st.metric(n, f"{d['price']:.2f}", f"{d['chg']:+.2f}%")
