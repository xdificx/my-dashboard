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

@st.cache_data(ttl=3600)
def get_ticker_name(ticker: str) -> str:
    """티커로 종목명 자동 조회 (1시간 캐시)"""
    try:
        info = yf.Ticker(ticker).info
        name = (info.get("longName")
                or info.get("shortName")
                or info.get("displayName")
                or "")
        return name.strip()
    except Exception:
        return ""
@st.cache_data(ttl=3600)
def get_stock_info(ticker: str) -> dict:
    """종목 세부정보 조회 (1시간 캐시)"""
    try:
        t    = yf.Ticker(ticker)
        info = t.info

        def fmt_num(v):
            if v is None: return None
            if v >= 1e12:  return f"{v/1e12:.2f}조"
            if v >= 1e8:   return f"{v/1e8:.2f}억"
            if v >= 1e4:   return f"{v/1e4:.2f}만"
            return f"{v:,.0f}"

        def pct(v):
            return f"{v*100:.2f}%" if v is not None else None

        def f2(v):
            return f"{v:.2f}" if v is not None else None

        def fcomma(v):
            return f"{v:,.2f}" if v is not None else None

        currency   = info.get("currency", "")
        exchange   = info.get("exchange", "")
        sector     = info.get("sector") or info.get("industry") or ""
        per        = info.get("trailingPE")
        fper       = info.get("forwardPE")
        pbr        = info.get("priceToBook")
        psr        = info.get("priceToSalesTrailing12Months")
        peg        = info.get("pegRatio")
        ev_ebitda  = info.get("enterpriseToEbitda")
        eps        = info.get("trailingEps")
        roe        = info.get("returnOnEquity")
        roa        = info.get("returnOnAssets")
        op_margin  = info.get("operatingMargins")
        profit_m   = info.get("profitMargins")
        rev_growth = info.get("revenueGrowth")
        earn_growth= info.get("earningsGrowth")
        div_yield  = info.get("dividendYield")
        div_rate   = info.get("dividendRate")
        payout     = info.get("payoutRatio")
        div5y      = info.get("fiveYearAvgDividendYield")
        debt_eq    = info.get("debtToEquity")
        cur_ratio  = info.get("currentRatio")
        beta       = info.get("beta")
        fcf        = info.get("freeCashflow")
        op_cf      = info.get("operatingCashflow")
        market_cap = info.get("marketCap")
        fcf_yield  = (fcf / market_cap * 100) if (fcf and market_cap) else None
        shares_out = info.get("sharesOutstanding")
        float_shr  = info.get("floatShares")
        avg_vol    = info.get("averageVolume")
        week52h    = info.get("fiftyTwoWeekHigh")
        week52l    = info.get("fiftyTwoWeekLow")

        return {
            "시가총액":       fmt_num(market_cap) if market_cap else None,
            "발행주식수":     fmt_num(shares_out) if shares_out else None,
            "유동주식수":     fmt_num(float_shr)  if float_shr  else None,
            "평균거래량":     fmt_num(avg_vol)     if avg_vol    else None,
            "52주 최고":      fcomma(week52h)      if week52h    else None,
            "52주 최저":      fcomma(week52l)      if week52l    else None,
            "PER":            f2(per)       if per       else None,
            "선행 PER":       f2(fper)      if fper      else None,
            "PBR":            f2(pbr)       if pbr       else None,
            "PSR":            f2(psr)       if psr       else None,
            "PEG":            f2(peg)       if peg       else None,
            "EV/EBITDA":      f2(ev_ebitda) if ev_ebitda else None,
            "EPS":            fcomma(eps)   if eps       else None,
            "ROE":            pct(roe)       if roe       else None,
            "ROA":            pct(roa)       if roa       else None,
            "영업이익률":     pct(op_margin) if op_margin else None,
            "순이익률":       pct(profit_m)  if profit_m  else None,
            "매출 성장률":    pct(rev_growth)  if rev_growth  else None,
            "이익 성장률":    pct(earn_growth) if earn_growth else None,
            "FCF":            fmt_num(fcf)   if fcf    else None,
            "영업현금흐름":   fmt_num(op_cf) if op_cf  else None,
            "FCF Yield":      f"{fcf_yield:.2f}%" if fcf_yield else None,
            "배당수익률":     pct(div_yield) if div_yield else None,
            "배당금(연간)":   fcomma(div_rate) if div_rate else None,
            "배당성향":       pct(payout)    if payout   else None,
            "5Y 평균배당수익률": f"{div5y:.2f}%" if div5y else None,
            "부채비율":       f"{debt_eq:.1f}%" if debt_eq else None,
            "유동비율":       f2(cur_ratio)  if cur_ratio else None,
            "베타(1Y)":       f2(beta)       if beta      else None,
            "섹터":   sector   if sector   else None,
            "거래소": exchange if exchange else None,
            "통화":   currency if currency else None,
        }
    except Exception:
        return {}
