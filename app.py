import streamlit as st
import pandas as pd
import numpy as np
import time

st.set_page_config(layout="wide")

st.title("📊 Quant Dashboard (Guaranteed Working)")

# -------------------------
# DUMMY DATA (NO API FAILURES)
# -------------------------
@st.cache_data(ttl=10)
def get_data():
    np.random.seed(42)
    price = np.cumsum(np.random.randn(200)) + 100
    df = pd.DataFrame({"Close": price})
    return df

df = get_data()

# -------------------------
# FEATURES
# -------------------------
df["ret"] = df["Close"].pct_change()
df["vol"] = df["ret"].rolling(10).std()
df["mean"] = df["Close"].rolling(20).mean()
df["std"] = df["Close"].rolling(20).std()
df["z"] = (df["Close"] - df["mean"]) / df["std"]

df.dropna(inplace=True)

# -------------------------
# REGIME
# -------------------------
latest = df.iloc[-1]

regime = "MR" if latest["vol"] < df["vol"].mean() else "TREND"

# -------------------------
# SIGNAL
# -------------------------
signal = "WAIT"

if regime == "MR":
    if latest["z"] < -1:
        signal = "BUY"
    elif latest["z"] > 1:
        signal = "SELL"
else:
    signal = "BUY" if latest["ret"] > 0 else "SELL"

# -------------------------
# UI
# -------------------------
c1, c2, c3 = st.columns(3)

c1.metric("Signal", signal)
c2.metric("Regime", regime)
c3.metric("Z-score", round(latest["z"], 2))

st.line_chart(df["Close"])

time.sleep(10)
st.rerun()
