import streamlit as st
import pandas as pd
import numpy as np
import requests
import time

st.set_page_config(layout="wide")

st.title("📊 Live Quant Dashboard (Cloud-Safe)")

# -------------------------
# SETTINGS
# -------------------------
REFRESH = st.sidebar.slider("Refresh (sec)", 10, 120, 30)

# -------------------------
# DATA (ROBUST - NO YFINANCE)
# -------------------------
@st.cache_data(ttl=30)
def get_data():
    try:
        # Free FX API (daily data, very stable on cloud)
        url = "https://api.exchangerate.host/timeseries?start_date=2024-01-01&end_date=2024-02-01&base=EUR&symbols=USD"
        res = requests.get(url, timeout=10).json()

        rates = res.get("rates", {})
        if not rates:
            return None

        df = pd.DataFrame(rates).T
        df.columns = ["Close"]
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()

        return df

    except Exception:
        return None

# -------------------------
# FEATURES
# -------------------------
def prepare(df):
    df["ret"] = df["Close"].pct_change()
    df["vol"] = df["ret"].rolling(10).std()
    df["vol_mean"] = df["vol"].rolling(20).mean()

    df["mean"] = df["Close"].rolling(15).mean()
    df["std"] = df["Close"].rolling(15).std()
    df["z"] = (df["Close"] - df["mean"]) / df["std"]

    df["ema_fast"] = df["Close"].ewm(span=5).mean()
    df["ema_slow"] = df["Close"].ewm(span=15).mean()

    df = df.dropna().copy()
    return df

# -------------------------
# REGIME
# -------------------------
def get_regime(df):
    latest = df.iloc[-1]

    if latest["vol"] < latest["vol_mean"]:
        regime = "MR"
    else:
        regime = "TREND"

    confidence = abs(latest["vol"] - latest["vol_mean"]) / (latest["vol_mean"] + 1e-9)
    return regime, confidence

# -------------------------
# SIGNAL
# -------------------------
def get_signal(df, regime):
    latest = df.iloc[-1]

    z = latest["z"]
    fast = latest["ema_fast"]
    slow = latest["ema_slow"]

    signal = "WAIT"

    if regime == "MR":
        if z < -1.5:
            signal = "BUY"
        elif z > 1.5:
            signal = "SELL"
    else:
        if fast > slow:
            signal = "BUY"
        else:
            signal = "SELL"

    return signal, z

# -------------------------
# MAIN
# -------------------------
df = get_data()

if df is None:
    st.error("❌ Data not loading (API issue)")
    st.stop()

df = prepare(df)

if df.empty:
    st.warning("Not enough data yet")
    st.stop()

regime, confidence = get_regime(df)
signal, z = get_signal(df, regime)

# -------------------------
# UI
# -------------------------
c1, c2, c3, c4 = st.columns(4)

c1.metric("Signal", signal)
c2.metric("Regime", regime)
c3.metric("Confidence", round(confidence, 2))
c4.metric("Z-score", round(z, 2))

st.line_chart(df["Close"])

# ALERT
if signal in ["BUY", "SELL"] and confidence > 0.4:
    st.warning("🚨 STRONG SIGNAL")

# DEBUG (optional)
with st.expander("Debug Data"):
    st.write(df.tail())

# -------------------------
# AUTO REFRESH
# -------------------------
time.sleep(REFRESH)
st.rerun()
