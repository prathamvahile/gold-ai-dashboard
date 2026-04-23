import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from hmmlearn.hmm import GaussianHMM
import time

st.set_page_config(layout="wide")

SYMBOL = "EURUSD=X"

# -------------------------
# AUTO REFRESH
# -------------------------
st.title("📊 Live Quant Dashboard")

refresh_rate = st.sidebar.slider("Refresh (seconds)", 10, 120, 60)
st.sidebar.write("Auto-refreshing...")

# -------------------------
# DATA
# -------------------------
@st.cache_data(ttl=60)
def get_data():
    df = yf.download(SYMBOL, interval="1m", period="2d")
    return df

def prepare(df):
    df['ret'] = df['Close'].pct_change()
    df['vol'] = df['ret'].rolling(10).std()

    df['mean'] = df['Close'].rolling(30).mean()
    df['std'] = df['Close'].rolling(30).std()
    df['z'] = (df['Close'] - df['mean']) / df['std']

    df['ema_fast'] = df['Close'].ewm(span=10).mean()
    df['ema_slow'] = df['Close'].ewm(span=30).mean()

    df.dropna(inplace=True)
    return df

# -------------------------
# HMM (cached)
# -------------------------
@st.cache_resource(ttl=300)
def train_hmm(df):
    X = df[['ret', 'vol']].values

    model = GaussianHMM(n_components=2, n_iter=100)
    model.fit(X)

    states = model.predict(X)

    vols = []
    for i in range(2):
        vols.append(np.std(X[states == i][:, 0]))

    mr_state = np.argmin(vols)

    return model, mr_state

# -------------------------
# SIGNAL
# -------------------------
def get_signal(df, model, mr_state):
    latest = df.iloc[-1]

    X = df[['ret', 'vol']].values
    probs = model.predict_proba(X)

    prob_mr = probs[-1][mr_state]

    if prob_mr > 0.65:
        regime = "MR"
    elif prob_mr < 0.35:
        regime = "TREND"
    else:
        regime = "NEUTRAL"

    z = latest['z']
    ema_fast = latest['ema_fast']
    ema_slow = latest['ema_slow']

    signal = "WAIT"

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

    return signal, regime, prob_mr, z

# -------------------------
# RUN
# -------------------------
df = get_data()
df = prepare(df)

model, mr_state = train_hmm(df)
signal, regime, prob, z = get_signal(df, model, mr_state)

# -------------------------
# UI
# -------------------------
col1, col2, col3, col4 = st.columns(4)

col1.metric("Signal", signal)
col2.metric("Regime", regime)
col3.metric("Confidence", round(prob, 2))
col4.metric("Z-score", round(z, 2))

st.line_chart(df['Close'])

# ALERT
if signal in ["BUY", "SELL"] and prob > 0.7:
    st.warning("🚨 STRONG SIGNAL!")

# -------------------------
# AUTO REFRESH LOGIC
# -------------------------
time.sleep(refresh_rate)
st.rerun()
