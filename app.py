import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests
import feedparser
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from datetime import datetime

st.set_page_config(layout="wide")

# -----------------------------
# AUTO REFRESH (60 sec)
# -----------------------------

# -----------------------------
# DARK UI
# -----------------------------
st.markdown("""
<style>
.stApp {background-color: #0B0F14;}
h1, h2, h3 {color: #00FFAA;}
p, span {color: #E6EDF3;}

div[data-testid="metric-container"] {
    background-color: #11161D;
    border: 1px solid #1F2A36;
    padding: 15px;
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)

st.title("📊 GOLD TERMINAL")

st.write("Last Updated:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

if st.button("🔄 Refresh Now"):
    st.rerun()

# -----------------------------
# LOAD DATA
# -----------------------------
@st.cache_data
def load_data(ticker):
    df = yf.download(ticker, period="3mo", interval="1d", progress=False)

    if df is None or df.empty:
        return pd.DataFrame()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    return df.dropna()

gold = load_data("GC=F")
usd = load_data("DX-Y.NYB")
yields = load_data("^TNX")
vix = load_data("^VIX")

# -----------------------------
# SIGNAL FUNCTION
# -----------------------------
def get_signal(df):
    try:
        close = df["Close"].dropna()
        if len(close) < 20:
            return 0

        last = float(close.iloc[-1])
        prev = float(close.iloc[-5])

        trend = 1 if last > prev else -1

        ma = close.rolling(20).mean()
        ma_last = float(ma.iloc[-1])

        ma_sig = 1 if last > ma_last else -1

        return (trend + ma_sig) / 2
    except:
        return 0

usd_sig = -get_signal(usd)
yield_sig = -get_signal(yields)
gold_sig = get_signal(gold)

# -----------------------------
# VIX RISK
# -----------------------------
try:
    vix_close = vix["Close"].dropna()
    vix_level = float(vix_close.iloc[-1])
    vix_prev = float(vix_close.iloc[-5])
    risk_sig = 1 if (vix_level > 20 and vix_level > vix_prev) else 0
except:
    risk_sig = 0

# -----------------------------
# NEWS
# -----------------------------
analyzer = SentimentIntensityAnalyzer()

def get_news():
    try:
        feed = feedparser.parse("https://news.google.com/rss/search?q=gold+war+inflation+fed")

        scores = []
        headlines = []

        for entry in feed.entries[:10]:
            text = entry.title.lower()
            sentiment = analyzer.polarity_scores(text)["compound"]

            if "war" in text:
                sentiment -= 0.3
            if "inflation" in text:
                sentiment -= 0.2
            if "rate hike" in text:
                sentiment += 0.2

            scores.append(sentiment)
            headlines.append(entry.title)

        avg = sum(scores)/len(scores) if scores else 0
        return avg, headlines[:5]

    except:
        return 0, ["No news"]

sentiment, headlines = get_news()

if sentiment < -0.2:
    news_bias = 0.5
elif sentiment > 0.2:
    news_bias = -0.5
else:
    news_bias = 0

# -----------------------------
# EVENTS
# -----------------------------
def get_events():
    try:
        url = "https://api.tradingeconomics.com/calendar?c=guest:guest&f=json"
        data = requests.get(url).json()

        events = []
        for e in data[:50]:
            if "United States" in e.get("Country",""):
                if any(x in e.get("Event","") for x in ["CPI","Fed","Interest"]):
                    events.append(f"{e['Event']} - {e['Date']}")

        return events[:5]

    except:
        return ["No event data"]

events = get_events()

# -----------------------------
# REGIME
# -----------------------------
def get_regime(gold, vix):
    try:
        close = gold["Close"].dropna()
        ma50 = close.rolling(50).mean().iloc[-1]
        price = float(close.iloc[-1])
        vix_val = float(vix["Close"].iloc[-1])

        if vix_val > 22:
            return "🔵 VOLATILE"

        deviation = abs(price - ma50) / ma50

        if deviation > 0.02:
            return "🟢 TRENDING"
        else:
            return "🟡 RANGE"

    except:
        return "UNKNOWN"

regime = get_regime(gold, vix)

# -----------------------------
# FINAL SCORE
# -----------------------------
score = usd_sig + yield_sig + gold_sig + risk_sig + news_bias

if score >= 2:
    bias = "STRONG BUY"
elif score >= 1:
    bias = "BUY"
elif score <= -2:
    bias = "STRONG SELL"
elif score <= -1:
    bias = "SELL"
else:
    bias = "NEUTRAL"

# -----------------------------
# CHART
# -----------------------------
def plot_chart(df):
    fig = go.Figure()
    if not df.empty:
        fig.add_trace(go.Scatter(x=df.index, y=df["Close"]))
    fig.update_layout(height=300)
    return fig

# -----------------------------
# UI
# -----------------------------
col1, col2 = st.columns([2,1])

with col1:
    st.subheader("📈 Gold Price")
    st.plotly_chart(plot_chart(gold), use_container_width=True, key="gold1")

with col2:
    st.subheader("📌 Market Summary")

    if "BUY" in bias:
        st.success(bias)
    elif "SELL" in bias:
        st.error(bias)
    else:
        st.warning(bias)

    st.write(f"Score: {round(score,2)}")
    st.write(f"Regime: {regime}")

# Signals
st.subheader("⚡ Signals")
c1,c2,c3,c4 = st.columns(4)
c1.metric("USD", round(usd_sig,2))
c2.metric("Yields", round(yield_sig,2))
c3.metric("Gold", round(gold_sig,2))
c4.metric("Risk", risk_sig)

# News & Events
colA,colB = st.columns(2)

with colA:
    st.subheader("🗓️ Events")
    for e in events:
        st.write(e)

with colB:
    st.subheader("📰 News")
    st.write(f"Sentiment: {round(sentiment,2)}")
    for h in headlines:
        st.write("• " + h)

# Extra charts
st.subheader("📊 Market Overview")
c1,c2 = st.columns(2)
c3,c4 = st.columns(2)

c1.plotly_chart(plot_chart(usd), use_container_width=True, key="usd")
c2.plotly_chart(plot_chart(yields), use_container_width=True, key="yields")
c3.plotly_chart(plot_chart(vix), use_container_width=True, key="vix")
c4.plotly_chart(plot_chart(gold), use_container_width=True, key="gold2")
import time

time.sleep(60)
st.rerun()