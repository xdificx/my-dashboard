import streamlit as st
from services.db_service import get_all_holdings
from services.data_service import get_history
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.title("📈 Chart")

holdings = get_all_holdings()

if holdings:
    selected = st.selectbox("종목 선택", [h["name"] for h in holdings])
    ticker = next(h["ticker"] for h in holdings if h["name"] == selected)

    hist = get_history(ticker)

    if not hist.empty:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True)
        fig.add_trace(go.Candlestick(
            x=hist.index,
            open=hist['Open'],
            high=hist['High'],
            low=hist['Low'],
            close=hist['Close']
        ), row=1, col=1)

        fig.add_trace(go.Bar(
            x=hist.index,
            y=hist['Volume']
        ), row=2, col=1)

        st.plotly_chart(fig, use_container_width=True)
