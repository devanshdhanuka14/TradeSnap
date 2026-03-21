import yfinance as yf
import pandas as pd

import requests
import os
from dotenv import load_dotenv
load_dotenv()

def fetch_stock_data(ticker: str, chart_period: str = "6mo"):
    stock = yf.Ticker(ticker)
    #fetching 1 year data for 52 week high low comparision
    df_1y = stock.history(period="1y")
    df_1y.drop(columns=["Dividends", "Stock Splits"], inplace=True)
    #for chart 6month data is enough
    df_chart = stock.history(period=chart_period)
    df_chart.drop(columns=["Dividends", "Stock Splits"], inplace=True)
    
    return df_chart, df_1y

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

    # Confluence of both trend and momentum
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

    return f"{verdict} · {trend} · RSI {rsi} ({momentum})"

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

def fetch_news(company_name: str, n: int = 3):
    api_key = os.getenv("NEWS_API_KEY")
    
    if not api_key:
        print("Error: NEWS_API_KEY not found in .env")
        return []
    
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": f'"{company_name}" stock OR shares OR NSE',
        "apiKey": api_key,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": n,
    }
    
    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        
        if data.get("status") != "ok":
            print(f"NewsAPI error: {data.get('message', 'Unknown error')}")
            return []
        
        articles = data.get("articles", [])[:n]
        
        if not articles:
            print(f"No articles found for: {company_name}")
            return []
        
        return [
            {
                "title": a.get("title", ""),
                "source": a.get("source", {}).get("name", ""),
                "url": a.get("url", "#"),
                "publishedAt": a.get("publishedAt", "")[:10],
            }
            for a in articles
        ]
    
    except requests.exceptions.Timeout:
        print("Error: NewsAPI request timed out")
        return []
    
    except requests.exceptions.ConnectionError:
        print("Error: No internet connection")
        return []
    
    except Exception as e:
        print(f"Unexpected error fetching news: {e}")
        return []



if __name__ == "__main__":
    df_chart, df_1y = fetch_stock_data("RELIANCE.NS", chart_period="6mo")
    df_chart = compute_indicators(df_chart)

    spike, ratio = is_volume_spike(df_chart)
    print(f"Volume spike: {spike} ({ratio}x average)")

    signal = get_signal(df_chart)
    print(f"Signal: {signal}")

    w52 = get_52w_position(df_1y)  # uses full 1 year data
    print(f"52W Position: {w52}")

    news = fetch_news("Reliance Industries")
    for article in news:
        print(f"- {article['title']} ({article['source']}, {article['publishedAt']})")