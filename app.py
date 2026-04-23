import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime

st.set_page_config(layout="wide")
st.title("📊 Quant Dashboard (Gold + EURUSD)")

REFRESH = st.sidebar.slider("Refresh (sec)", 10, 120, 30)
ASSET = st.sidebar.selectbox("Select Asset", ["GOLD", "EURUSD"])

# -------------------------
# DATA (ROBUST YAHOO CSV)
# -------------------------
@st.cache_data(ttl=60)
def get_data(asset):
    try:
        end = int(datetime.now().timestamp())
        start = end - 60 * 60 * 24 * 365  # 1 year

        if asset == "GOLD":
            symbol = "GC=F"  # Gold Futures
        else:
            symbol = "EURUSD=X"

        url = f"https://query1.finance.yahoo.com/v7/finance/download/{symbol}?period1={start}&period2={end}&interval=1d&events=history"

        df = pd.read_csv(url)

        df["Date"] = pd.to_datetime(df["Date"])
        df.set_index("Date", inplace=True)

        df = df[["Close"]].dropna()

        return df

    except Exception as e:
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
# SIGNAL
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
# BACKTEST
# -------------------------
def backtest(df):
    capital = 10000
    position = 0
    entry_price = 0

    trades = []
    equity = []

    for i in range(50, len(df)):
        sub = df.iloc[:i]

        regime, _ = get_regime(sub)
        signal, _ = get_signal(sub, regime)

        price = df["Close"].iloc[i]

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

    return capital, trades, equity

# -------------------------
# MAIN
# -------------------------
df = get_data(ASSET)

if df is None or df.empty:
    st.error("❌ Data failed (Yahoo blocked or network issue)")
    st.stop()

df = prepare(df)

regime, confidence = get_regime(df)
signal, z = get_signal(df, regime)

capital, trades, equity = backtest(df)

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

st.subheader("📊 Performance")

p1, p2, p3 = st.columns(3)
p1.metric("Capital", round(capital, 2))
p2.metric("Trades", len(trades))
p3.metric("Win Rate %", round(win_rate, 2))

st.subheader("📈 Equity Curve")
st.line_chart(pd.Series(equity))
