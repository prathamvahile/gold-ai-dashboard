import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime

st.set_page_config(layout="wide")
st.title("⚡ Live Trading Signals (Gold + EURUSD)")

REFRESH = st.sidebar.slider("Refresh (sec)", 10, 120, 30)
ASSET = st.sidebar.selectbox("Asset", ["GOLD", "EURUSD"])

# -------------------------
# LIVE DATA (YAHOO CSV)
# -------------------------
@st.cache_data(ttl=30)
def get_data(asset):
    try:
        end = int(datetime.now().timestamp())
        start = end - 60 * 60 * 24 * 60  # last 60 days

        symbol = "GC=F" if asset == "GOLD" else "EURUSD=X"

        url = f"https://query1.finance.yahoo.com/v7/finance/download/{symbol}?period1={start}&period2={end}&interval=1d&events=history"

        df = pd.read_csv(url)

        df["Date"] = pd.to_datetime(df["Date"])
        df.set_index("Date", inplace=True)

        df = df[["Close"]].dropna()

        return df

    except:
        return None

# -------------------------
# FEATURES
# -------------------------
def prepare(df):
    df["ret"] = df["Close"].pct_change()

    df["vol"] = df["ret"].rolling(10).std()
    df["vol_mean"] = df["vol"].rolling(20).mean()

    df["mean"] = df["Close"].rolling(20).mean()
    df["std"] = df["Close"].rolling(20).std()
    df["z"] = (df["Close"] - df["mean"]) / df["std"]

    df["ema_fast"] = df["Close"].ewm(span=5).mean()
    df["ema_slow"] = df["Close"].ewm(span=15).mean()

    df.dropna(inplace=True)
    return df

# -------------------------
# REGIME
# -------------------------
def get_regime(df):
    latest = df.iloc[-1]

    if latest["vol"] < latest["vol_mean"]:
        return "MEAN REVERSION"
    else:
        return "TREND"

# -------------------------
# SIGNAL
# -------------------------
def get_signal(df, regime):
    latest = df.iloc[-1]

    z = latest["z"]
    fast = latest["ema_fast"]
    slow = latest["ema_slow"]

    if regime == "MEAN REVERSION":
        if z < -2:
            return "BUY"
        elif z > 2:
            return "SELL"
        else:
            return "WAIT"

    else:
        if fast > slow:
            return "BUY"
        else:
            return "SELL"

# -------------------------
# MAIN
# -------------------------
df = get_data(ASSET)

if df is None or df.empty:
    st.error("❌ Data failed")
    st.stop()

df = prepare(df)

regime = get_regime(df)
signal = get_signal(df, regime)
price = df["Close"].iloc[-1]
z = df["z"].iloc[-1]

# -------------------------
# UI
# -------------------------
c1, c2, c3, c4 = st.columns(4)

c1.metric("Asset", ASSET)
c2.metric("Signal", signal)
c3.metric("Regime", regime)
c4.metric("Price", round(price, 2))

st.subheader("Z-score")
st.metric("Z", round(z, 2))

st.line_chart(df["Close"])

# ALERT
if signal in ["BUY", "SELL"]:
    st.warning("🚨 SIGNAL DETECTED")

# AUTO REFRESH
time.sleep(REFRESH)
st.rerun()
