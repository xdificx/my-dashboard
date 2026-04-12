import yfinance as yf
import pandas as pd
import streamlit as st
from concurrent.futures import ThreadPoolExecutor, as_completed

# ══════════════════════════════════════════════════
#  단일 티커 조회
# ══════════════════════════════════════════════════
@st.cache_data(ttl=60)
def get_ticker_data(ticker: str) -> dict:
    try:
        info  = yf.Ticker(ticker).fast_info
        price = info.last_price or getattr(info, 'current_price', None)
        prev  = info.previous_close
        if price and prev:
            chg = (price - prev) / prev * 100
            return {"price": round(price, 2), "chg": round(chg, 2), "ok": True}
    except Exception:
        pass
    return {"price": None, "chg": None, "ok": False}

# ══════════════════════════════════════════════════
#  복수 티커 병렬 조회 (ThreadPoolExecutor)
# ══════════════════════════════════════════════════
@st.cache_data(ttl=60)
def get_multiple_tickers(ticker_label_pairs: tuple) -> dict:
    """
    여러 티커를 병렬로 동시 조회
    ticker_label_pairs: ((ticker, label), ...) 형태의 tuple

    반환: {ticker: {"label", "price", "chg", "ok"}, ...}
    """
    def _fetch(ticker: str, label: str) -> tuple:
        d = get_ticker_data(ticker)
        d["label"] = label
        return ticker, d

    results = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(_fetch, ticker, label): ticker
            for ticker, label in ticker_label_pairs
        }
        for future in as_completed(futures):
            try:
                ticker, data = future.result()
                results[ticker] = data
            except Exception:
                ticker = futures[future]
                results[ticker] = {"label": ticker, "price": None,
                                   "chg": None, "ok": False}

    # 원래 순서 유지
    ordered = {}
    for ticker, label in ticker_label_pairs:
        ordered[ticker] = results.get(ticker, {
            "label": label, "price": None, "chg": None, "ok": False
        })
    return ordered

# ══════════════════════════════════════════════════
#  히스토리 조회
# ══════════════════════════════════════════════════
@st.cache_data(ttl=300)
def get_history(ticker: str, period: str = "1y", interval: str = "1d"):
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False)
        if df is not None and not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

# ══════════════════════════════════════════════════
#  보유 종목 현재가 병렬 조회
# ══════════════════════════════════════════════════
@st.cache_data(ttl=60)
def get_holdings_prices(ticker_tuple: tuple) -> dict:
    """
    보유 종목 현재가를 병렬로 조회
    ticker_tuple: (ticker1, ticker2, ...) 형태의 tuple

    반환: {ticker: price or None, ...}
    """
    def _fetch_price(ticker: str):
        d = get_ticker_data(ticker)
        return ticker, d["price"] if d["ok"] else None

    results = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(_fetch_price, t): t for t in ticker_tuple}
        for future in as_completed(futures):
            try:
                ticker, price = future.result()
                results[ticker] = price
            except Exception:
                results[futures[future]] = None
    return results
