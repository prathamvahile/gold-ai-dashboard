import streamlit as st
import pandas as pd
import numpy as np
import requests
import time

st.set_page_config(layout="wide")
st.title("📊 Quant Dashboard (Gold + EURUSD)")

REFRESH = st.sidebar.slider("Refresh (sec)", 10, 120, 30)
ASSET = st.sidebar.selectbox("Select Asset", ["GOLD", "EURUSD"])

# -------------------------
# DATA (STABLE FOR BOTH)
# -------------------------
@st.cache_data(ttl=60)
def get_data(asset):
    try:
        if asset == "EURUSD":
            url = "https://api.exchangerate.host/timeseries?start_date=2023-01-01&end_date=2024-01-01&base=EUR&symbols=USD"
        else:
            url = "https://api.exchangerate.host/timeseries?start_date=2023-01-01&end_date=2024-01-01&base=XAU&symbols=USD"

        res = requests.get(url, timeout=10).json()
        rates = res.get("rates", {})

        if not rates:
            return None

        df = pd.DataFrame(rates).T
        df.columns = ["Close"]
        df.index = pd.to_datetime(df.index)
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
    df["vol_mean"] = df["vol"].rolling(30).mean()

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
        regime = "MR"
    else:
        regime = "TREND"

    confidence = abs(latest["vol"] - latest["vol_mean"]) / (latest["vol_mean"] + 1e-9)
    return regime, confidence

# -------------------------
# SIGNAL (IMPROVED)
# -------------------------
def get_signal(df, regime):
    latest = df.iloc[-1]

    z = latest["z"]
    fast = latest["ema_fast"]
    slow = latest["ema_slow"]
    ret = latest["ret"]

    signal = "WAIT"

    if regime == "MR":
        if z < -2:
            signal = "BUY"
        elif z > 2:
            signal = "SELL"
    else:
        if ret > 0.002 and fast > slow:
            signal = "BUY"
        elif ret < -0.002 and fast < slow:
            signal = "SELL"

    return signal, z

# -------------------------
# BACKTEST + TRACKING
# -------------------------
def backtest(df):
    capital = 10000
    position = 0
    entry_price = 0

    trades = []
    signals = []
    equity = []

    for i in range(50, len(df)):
        sub = df.iloc[:i]

        regime, _ = get_regime(sub)
        signal, _ = get_signal(sub, regime)

        price = df["Close"].iloc[i]
        signals.append(signal)

        if position == 0:
            if signal == "BUY":
                position = 1
                entry_price = price
            elif signal == "SELL":
                position = -1
                entry_price = price

        elif position == 1:
            pnl = price - entry_price
            if pnl > 2 or pnl < -2:
                capital += pnl
                trades.append(pnl)
                position = 0

        elif position == -1:
            pnl = entry_price - price
            if pnl > 2 or pnl < -2:
                capital += pnl
                trades.append(pnl)
                position = 0

        equity.append(capital)

    return capital, trades, signals, equity

# -------------------------
# MAIN
# -------------------------
df = get_data(ASSET)

if df is None:
    st.error("❌ Data failed")
    st.stop()

df = prepare(df)

if df.empty:
    st.warning("Not enough data")
    st.stop()

regime, confidence = get_regime(df)
signal, z = get_signal(df, regime)

capital, trades, signals, equity = backtest(df)

# -------------------------
# METRICS
# -------------------------
win_rate = 0
if trades:
    wins = [t for t in trades if t > 0]
    win_rate = len(wins) / len(trades) * 100

# -------------------------
# UI
# -------------------------
c1, c2, c3, c4 = st.columns(4)

c1.metric("Signal", signal)
c2.metric("Regime", regime)
c3.metric("Confidence", round(confidence, 2))
c4.metric("Z-score", round(z, 2))

st.line_chart(df["Close"])

# Performance
st.subheader("📊 Performance")

p1, p2, p3 = st.columns(3)
p1.metric("Final Capital", round(capital, 2))
p2.metric("Trades", len(trades))
p3.metric("Win Rate %", round(win_rate, 2))

# Equity curve
st.subheader("📈 Equity Curve")
st.line_chart(pd.Series(equity))

# Signal history
st.subheader("📡 Recent Signals")
st.write(signals[-20:])

# Trades
st.subheader("📉 Recent Trades")
st.write(trades[-20:])

# Alert
if signal in ["BUY", "SELL"] and confidence > 0.5:
    st.warning("🚨 STRONG SIGNAL")

# Refresh
time.sleep(REFRESH)
st.rerun()
