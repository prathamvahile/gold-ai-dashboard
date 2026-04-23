import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time

st.set_page_config(layout="wide")

SYMBOL = "EURUSD=X"

st.title("📊 Live Quant Dashboard (Cloud Version)")

# -------------------------
# AUTO REFRESH CONTROL
# -------------------------
refresh_rate = st.sidebar.slider("Refresh (seconds)", 10, 120, 60)

# -------------------------
# DATA LOADING (SAFE)
# -------------------------
@st.cache_data(ttl=60)
def get_data():
    try:
        df = yf.download(SYMBOL, interval="5m", period="5d")

        if df is None or df.empty:
            return None

        if 'Close' not in df.columns:
            return None

        return df

    except:
        return None

# -------------------------
# FEATURE ENGINEERING
# -------------------------
def prepare(df):
    df['ret'] = df['Close'].pct_change()
    df['vol'] = df['ret'].rolling(20).std()
    df['vol_mean'] = df['vol'].rolling(50).mean()

    df['mean'] = df['Close'].rolling(30).mean()
    df['std'] = df['Close'].rolling(30).std()
    df['z'] = (df['Close'] - df['mean']) / df['std']

    df['ema_fast'] = df['Close'].ewm(span=10).mean()
    df['ema_slow'] = df['Close'].ewm(span=30).mean()

    df.dropna(inplace=True)
    return df

# -------------------------
# REGIME DETECTION (NO HMM)
# -------------------------
def get_regime(df):
    latest = df.iloc[-1]

    vol = latest['vol']
    vol_mean = latest['vol_mean']

    if vol < vol_mean:
        regime = "MR"
    else:
        regime = "TREND"

    confidence = abs(vol - vol_mean) / (vol_mean + 1e-9)

    return regime, confidence

# -------------------------
# SIGNAL LOGIC
# -------------------------
def get_signal(df, regime, confidence):
    latest = df.iloc[-1]

    z = latest['z']
    ema_fast = latest['ema_fast']
    ema_slow = latest['ema_slow']

    signal = "WAIT"

    # Strong filtering
    if regime == "MR":
        if z < -1.8:
            signal = "BUY"
        elif z > 1.8:
            signal = "SELL"

    elif regime == "TREND":
        if ema_fast > ema_slow:
            signal = "BUY"
        else:
            signal = "SELL"

    return signal, z

# -------------------------
# MAIN RUN
# -------------------------
df = get_data()

if df is None:
    st.error("❌ Data not loading. Try again.")
    st.stop()

df = prepare(df)

regime, confidence = get_regime(df)
signal, z = get_signal(df, regime, confidence)

# -------------------------
# UI
# -------------------------
col1, col2, col3, col4 = st.columns(4)

col1.metric("Signal", signal)
col2.metric("Regime", regime)
col3.metric("Confidence", round(confidence, 2))
col4.metric("Z-score", round(z, 2))

st.line_chart(df['Close'])

# -------------------------
# ALERT
# -------------------------
if signal in ["BUY", "SELL"] and confidence > 0.5:
    st.warning("🚨 STRONG SIGNAL!")

# -------------------------
# DEBUG (optional)
# -------------------------
with st.expander("Debug Data"):
    st.write(df.tail())

# -------------------------
# AUTO REFRESH
# -------------------------
time.sleep(refresh_rate)
st.rerun()
