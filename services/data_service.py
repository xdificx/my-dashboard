import yfinance as yf
import pandas as pd
import streamlit as st

@st.cache_data(ttl=60)
def get_ticker_data(ticker: str):
    try:
        stock = yf.Ticker(ticker)
        info  = stock.fast_info
        price = info.last_price or getattr(info, 'current_price', None)
        prev  = info.previous_close
        if price and prev:
            chg = (price - prev) / prev * 100
            return {"price": round(price, 2), "chg": round(chg, 2), "ok": True}
    except:
        pass
    return {"price": None, "chg": None, "ok": False}

@st.cache_data(ttl=300)
def get_history(ticker: str, period: str = "1y", interval: str = "1d"):
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False)
        if df is not None and not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
        return df if df is not None else pd.DataFrame()
    except:
        return pd.DataFrame()
