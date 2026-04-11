import streamlit as st
import pandas as pd

def render_portfolio_table(rows):
    df = pd.DataFrame(rows)

    def color_style(v):
        if isinstance(v, (int, float)):
            return "color:#e24b4a; font-weight:600" if v > 0 else "color:#378add; font-weight:600"
        return ""

    st.dataframe(
        df.style.map(color_style, subset=["수익률(%)"])
                .map(color_style, subset=["평가손익(원)"]),
        use_container_width=True,
        hide_index=True
    )
