import streamlit as st
import pandas as pd
import numpy as np
import requests
import time

st.set_page_config(layout="wide")
st.title("⚡ Live Signals (Gold + EURUSD)")

# 🔑 Your API Key (already added)
API_KEY = "QLUPEQV4GYWP7US9"

ASSET = st.sidebar.selectbox("Asset", ["EURUSD", "GOLD"])
REFRESH = st.sidebar.slider("Refresh (sec)", 30, 120, 60)

# -------------------------
# DATA
# -------------------------
@st.cache_data(ttl=60)
def get_data(asset):
    try:
        if asset == "EURUSD":
            url = f"https://www.alphavantage.co/query?function=FX_DAILY&from_symbol=EUR&to_symbol=USD&apikey={API_KEY}"
            data = requests.get(url).json()

            if "Time Series FX (Daily)" not in data:
                return None

            df = pd.DataFrame(data["Time Series FX (Daily)"]).T
            df = df.rename(columns={"4. close": "Close"})

        else:
            # GOLD via USD proxy (Alpha Vantage doesn't directly support XAU well)
            url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=GLD&apikey={API_KEY}"
            data = requests.get(url).json()

            if "Time Series (Daily)" not in data:
                return None

            df = pd.DataFrame(data["Time Series (Daily)"]).T
            df = df.rename(columns={"4. close": "Close"})

        df.index = pd.to_datetime(df.index)
        df["Close"] = df["Close"].astype(float)
        df.sort_index(inplace=True)

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
# SIGNAL
# -------------------------
def get_signal(df):
    latest = df.iloc[-1]

    if latest["vol"] < latest["vol_mean"]:
        regime = "MEAN REVERSION"
        if latest["z"] < -2:
            signal = "BUY"
        elif latest["z"] > 2:
            signal = "SELL"
        else:
            signal = "WAIT"
    else:
        regime = "TREND"
        if latest["ema_fast"] > latest["ema_slow"]:
            signal = "BUY"
        else:
            signal = "SELL"

    return signal, regime

# -------------------------
# MAIN
# -------------------------
df = get_data(ASSET)

if df is None or df.empty:
    st.error("❌ Data failed (API limit or invalid key)")
    st.stop()

df = prepare(df)

signal, regime = get_signal(df)

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

st.metric("Z-score", round(z, 2))
st.line_chart(df["Close"])

if signal in ["BUY", "SELL"]:
    st.warning("🚨 SIGNAL DETECTED")

# -------------------------
# REFRESH
# -------------------------
time.sleep(REFRESH)
st.rerun()
