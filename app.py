import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import feedparser
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from datetime import datetime
import time

st.set_page_config(layout="wide")
st.title("📊 GOLD TERMINAL")

st.write("Last Updated:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

# -----------------------------
# LOAD DATA
# -----------------------------
@st.cache_data
def load_data(ticker):
    try:
        df = yf.download(ticker, period="3mo", interval="1d", progress=False)
        if df is None or df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df.dropna()
    except:
        return pd.DataFrame()

gold = load_data("GC=F")
usd = load_data("DX-Y.NYB")
yields = load_data("^TNX")
vix = load_data("^VIX")

# -----------------------------
# SIGNALS
# -----------------------------
def get_signal(df):
    try:
        close = df["Close"].dropna()
        if len(close) < 20:
            return 0

        last = float(close.iloc[-1])
        prev = float(close.iloc[-5])

        trend = 1 if last > prev else -1
        ma = close.rolling(20).mean().iloc[-1]

        ma_sig = 1 if last > ma else -1

        return (trend + ma_sig) / 2
    except:
        return 0

usd_sig = -get_signal(usd)
yield_sig = -get_signal(yields)
gold_sig = get_signal(gold)

# -----------------------------
# VIX
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
        scores, headlines = [], []

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
# REGIME
# -----------------------------
def get_regime(gold, vix):
    try:
        close = gold["Close"].dropna()
        ma50 = close.rolling(50).mean().iloc[-1]
        price = float(close.iloc[-1])
        vix_val = float(vix["Close"].iloc[-1])

        if vix_val > 22:
            return "VOLATILE"

        deviation = abs(price - ma50) / ma50

        if deviation > 0.02:
            return "TRENDING"
        else:
            return "RANGE"

    except:
        return "UNKNOWN"

regime = get_regime(gold, vix)

# -----------------------------
# SCORE & BIAS
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
# STRATEGY
# -----------------------------
def get_strategy(regime):
    if regime == "TRENDING":
        return "➡️ Breakout / Trend Following"
    elif regime == "RANGE":
        return "➡️ Mean Reversion"
    elif regime == "VOLATILE":
        return "➡️ Avoid or Reduce Position Size"
    else:
        return "➡️ No clear strategy"

strategy = get_strategy(regime)

# -----------------------------
# DO NOT TRADE FILTER
# -----------------------------
def do_not_trade(score, regime, sentiment):
    if -0.5 < score < 0.5:
        return True, "Low conviction"
    if regime == "VOLATILE":
        return True, "High volatility"
    if abs(sentiment) < 0.05:
        return True, "No strong news direction"
    return False, ""

avoid, reason = do_not_trade(score, regime, sentiment)

# -----------------------------
# AI-LIKE REPORT (NO API)
# -----------------------------
def generate_report():
    text = f"Bias: {bias}, Regime: {regime}. "

    if "BUY" in bias:
        text += "Gold has bullish support. "
    elif "SELL" in bias:
        text += "Gold faces bearish pressure. "
    else:
        text += "Market is neutral. "

    if regime == "TRENDING":
        text += "Trend-following strategies are preferred. "
    elif regime == "RANGE":
        text += "Mean reversion strategies work better. "
    else:
        text += "Volatility is high, avoid aggressive trading. "

    if avoid:
        text += f"⚠️ Avoid trading: {reason}."

    return text

# -----------------------------
# CHART
# -----------------------------
def plot_chart(df):
    fig = go.Figure()
    if not df.empty:
        fig.add_trace(go.Scatter(x=df.index, y=df["Close"]))
    return fig

# -----------------------------
# UI
# -----------------------------
st.subheader("📈 Gold Chart")
st.plotly_chart(plot_chart(gold), use_container_width=True)

st.subheader("📊 Market Summary")
st.write("Bias:", bias)
st.write("Score:", round(score,2))
st.write("Regime:", regime)
st.write("Strategy:", strategy)

if avoid:
    st.error(f"🚫 DO NOT TRADE: {reason}")
else:
    st.success("✅ Trading conditions acceptable")

st.subheader("📰 News")
for h in headlines:
    st.write("-", h)

st.subheader("🧠 Market Report")
st.write(generate_report())

# -----------------------------
# AUTO REFRESH
# -----------------------------
time.sleep(60)
st.rerun()
