import yfinance as yf
import pandas as pd

def fetch_stock_data(ticker: str, period: str = "6mo"):
    stock = yf.Ticker(ticker)
    df = stock.history(period=period)
    df.drop(columns=["Dividends", "Stock Splits"], inplace=True)
    return df

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


if __name__ == "__main__":
    df = fetch_stock_data("RELIANCE.NS")
    df = compute_indicators(df)
    print(df[["Close", "MA20", "MA50", "RSI", "Volume", "AvgVol20"]].tail())
    
    spike, ratio = is_volume_spike(df)
    print(f"\nVolume spike: {spike} ({ratio}x average)")
    
    signal = get_signal(df)
    print(f"Signal: {signal}")