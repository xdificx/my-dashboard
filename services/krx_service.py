import streamlit as st
import pandas as pd
import os

# CSV 파일 경로 (GitHub 레포 기준)
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KOSPI_CSV  = os.path.join(BASE_DIR, "data", "kospi.csv")
KOSDAQ_CSV = os.path.join(BASE_DIR, "data", "kosdaq.csv")


@st.cache_data(ttl=86400)  # 24시간 캐시
def get_krx_stock_list() -> list:
    """
    CSV 파일에서 코스피 + 코스닥 전체 종목 목록 로드
    반환: [{"name": "삼성전자", "code": "005930", "ticker": "005930.KS", "market": "KOSPI"}, ...]
    """
    stocks = []

    file_map = [
        (KOSPI_CSV,  "KOSPI",  ".KS"),
        (KOSDAQ_CSV, "KOSDAQ", ".KQ"),
    ]

    for filepath, market, suffix in file_map:
        if not os.path.exists(filepath):
            continue
        try:
            df = pd.read_csv(filepath, encoding="cp949", dtype=str)
            df.columns = df.columns.str.strip()

            code_col = "단축코드"
            name_col = "한글 종목약명"

            if code_col not in df.columns or name_col not in df.columns:
                continue

            df = df[[code_col, name_col]].dropna()
            df[code_col] = df[code_col].str.strip().str.zfill(6)
            df[name_col] = df[name_col].str.strip()

            for _, row in df.iterrows():
                code = row[code_col]
                name = row[name_col]
                if code and name:
                    stocks.append({
                        "name":   name,
                        "code":   code,
                        "ticker": f"{code}{suffix}",
                        "market": market,
                    })
        except Exception:
            continue

    return stocks


def search_stocks(query: str, stocks: list, limit: int = 10) -> list:
    """종목명 또는 종목코드로 검색"""
    if not query or not stocks:
        return []

    q       = query.strip()
    q_upper = q.upper()

    exact    = [s for s in stocks
                if s["code"] == q.zfill(6) or s["ticker"].upper() == q_upper]
    starts   = [s for s in stocks
                if s["name"].startswith(q) and s not in exact]
    contains = [s for s in stocks
                if q in s["name"] and s not in exact and s not in starts]

    return (exact + starts + contains)[:limit]
