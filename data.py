import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import requests
import os
from dotenv import load_dotenv
load_dotenv()

import requests
from requests.adapters import HTTPAdapter

def fetch_stock_data(ticker: str, chart_period: str = "6mo"):
    try:
        stock = yf.Ticker(ticker)

        df_1y = stock.history(period="1y")
        df_chart = stock.history(period=chart_period)

        if df_1y.empty or df_chart.empty:
            print(f"Error: No data found for {ticker}")
            return None, None, None

        df_1y.drop(columns=["Dividends", "Stock Splits"], inplace=True)
        df_chart.drop(columns=["Dividends", "Stock Splits"], inplace=True)

        company_name = stock.info.get("longName", ticker)

        return df_chart, df_1y, company_name

    except Exception as e:
        return None, None, str(e)
    
def compute_indicators(df: pd.DataFrame):
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()

    # RSI
    delta = df["Close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    # Average volume
    df["AvgVol20"] = df["Volume"].rolling(20).mean()

    return df

def is_volume_spike(df: pd.DataFrame, threshold: float = 1.5):
    last = df.iloc[-1]
    vol = last["Volume"]
    avg = last["AvgVol20"]
    if pd.isna(avg) or avg == 0:
        return False, 0.0
    ratio = vol / avg
    spike = ratio >= threshold
    return spike, round(ratio, 2)

def get_signal(df: pd.DataFrame):
    last = df.iloc[-1]
    price = last["Close"]
    ma20 = last["MA20"]
    ma50 = last["MA50"]
    rsi = round(last["RSI"], 1)

    above_ma20 = price > ma20
    above_ma50 = price > ma50

    # Trend
    if above_ma20 and above_ma50:
        trend = "Bullish structure"
    elif above_ma20 and not above_ma50:
        trend = "Short-term strength, long-term weak"
    elif not above_ma20 and above_ma50:
        trend = "Short-term weakness, long-term hold"
    else:
        trend = "Bearish structure"

    # Momentum
    if rsi > 70:
        momentum = "overbought — watch for reversal"
    elif rsi > 55:
        momentum = "bullish momentum"
    elif rsi > 45:
        momentum = "neutral"
    elif rsi > 30:
        momentum = "bearish momentum"
    else:
        momentum = "oversold — watch for bounce"

    # Confluence
    if above_ma20 and above_ma50 and rsi > 55 and rsi <= 70:
        verdict = "STRONG BUY SIGNAL"
    elif above_ma20 and above_ma50 and rsi > 70:
        verdict = "BULLISH BUT OVEREXTENDED"
    elif not above_ma20 and not above_ma50 and rsi < 45 and rsi >= 30:
        verdict = "STRONG SELL SIGNAL"
    elif not above_ma20 and not above_ma50 and rsi < 30:
        verdict = "BEARISH BUT OVERSOLD"
    elif above_ma20 and above_ma50 and rsi < 45:
        verdict = "BULLISH STRUCTURE, WEAK MOMENTUM — WAIT"
    elif not above_ma20 and not above_ma50 and rsi > 55:
        verdict = "BEARISH STRUCTURE, STRONG MOMENTUM — CONFLICTED"
    else:
        verdict = "MIXED SIGNALS"

    # Reasoning
    ma20_diff = round(((price - ma20) / ma20) * 100, 2)
    ma50_diff = round(((price - ma50) / ma50) * 100, 2)

    reasoning = (
        f"Price is {'above' if above_ma20 else 'below'} MA20 by {abs(ma20_diff)}% "
        f"and {'above' if above_ma50 else 'below'} MA50 by {abs(ma50_diff)}%. "
        f"RSI at {rsi} indicates {momentum}."
    )

    return verdict, trend, reasoning

def get_52w_position(df: pd.DataFrame):
    high52 = df["High"].max()
    low52 = df["Low"].min()
    current = df.iloc[-1]["Close"]

    position_pct = (current - low52) / (high52 - low52) * 100
    pct_from_low = (current - low52) / low52 * 100
    pct_from_high = (high52 - current) / high52 * 100

    return {
        "52w_high": round(high52, 2),
        "52w_low": round(low52, 2),
        "current": round(current, 2),
        "position_pct": round(position_pct, 1),
        "pct_from_low": round(pct_from_low, 1),
        "pct_from_high": round(pct_from_high, 1),
    }

def fetch_news(ticker: str, n: int = 3):
    import feedparser
    
    # Convert ticker to search query
    # RELIANCE.NS -> Reliance Industries NSE stock
    symbol = ticker.replace(".NS", "")
    query = f"{symbol} NSE stock"
    query_encoded = query.replace(" ", "+")
    
    url = f"https://news.google.com/rss/search?q={query_encoded}&hl=en-IN&gl=IN&ceid=IN:en"
    
    try:
        feed = feedparser.parse(url)
        
        if not feed.entries:
            print(f"No news found for {ticker}")
            return []
        
        articles = []
        for entry in feed.entries[:n]:
            articles.append({
                "title": entry.get("title", ""),
                "source": entry.get("source", {}).get("title", "Google News"),
                "url": entry.get("link", "#"),
                "publishedAt": entry.get("published", "")[:16],
            })
        
        return articles
    
    except Exception as e:
        print(f"Error fetching news for {ticker}: {e}")
        return []
    

if __name__ == "__main__":
    df_chart, df_1y, company_name = fetch_stock_data("RELIANCE.NS", chart_period="6mo")
    print(f"Company: {company_name}")
    df_chart = compute_indicators(df_chart)

    spike, ratio = is_volume_spike(df_chart)
    print(f"Volume spike: {spike} ({ratio}x average)")

    verdict, trend, reasoning = get_signal(df_chart)
    print(f"Verdict: {verdict}")
    print(f"Trend: {trend}")
    print(f"Reasoning: {reasoning}")

    w52 = get_52w_position(df_1y)  # uses full 1 year data
    print(f"52W Position: {w52}")

    news = fetch_news("RELIANCE.NS")
    for article in news:
        print(f"- {article['title']} ({article['source']}, {article['publishedAt']})")