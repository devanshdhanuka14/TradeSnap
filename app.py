import streamlit as st
from data import fetch_stock_data, compute_indicators, is_volume_spike, get_signal, get_52w_position, fetch_news

st.set_page_config(
    page_title="TradeSnap",
    page_icon="📈",
    layout="wide"
)

st.title("📈 TradeSnap")
st.caption("Daily Stock Snapshot · NSE Morning Briefing")

with st.sidebar:
    st.header("Watchlist")
    
    watchlist_input = st.text_area(
        label="Enter tickers (one per line)",
        value="RELIANCE.NS\nTCS.NS\nINFY.NS",
        height=200,
        help="Use NSE format — e.g. RELIANCE.NS, HDFCBANK.NS"
    )
    
    chart_period = st.selectbox(
        "Chart Period",
        options=["1mo", "3mo", "6mo", "1y"],
        index=2
    )
    
    vol_threshold = st.slider(
        "Volume Spike Threshold (× average)",
        min_value=1.2,
        max_value=3.0,
        value=1.5,
        step=0.1
    )
    
    run = st.button("Run Briefing", use_container_width=True)

tickers = [t.strip().upper() for t in watchlist_input.strip().splitlines() if t.strip()]
tickers = [t + ".NS" if not t.endswith(".NS") else t for t in tickers]
tickers = tickers[:10]

if run:
    if not tickers:
        st.error("Please enter at least one ticker.")
    else:
        for ticker in tickers:
            st.subheader(ticker)
            
            df_chart, df_1y = fetch_stock_data(ticker, chart_period)
            
            if df_chart is None:
                st.warning(f"Could not fetch data for {ticker}. Check the ticker symbol.")
                continue
            
            df_chart = compute_indicators(df_chart)
            
            spike, ratio = is_volume_spike(df_chart, vol_threshold)
            signal = get_signal(df_chart)
            w52 = get_52w_position(df_1y)
            
            last = df_chart.iloc[-1]
            prev_close = df_chart.iloc[-2]["Close"]

            price = last["Close"]
            change = price - prev_close
            change_pct = (change / prev_close) * 100

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Price", f"₹{price:,.2f}", f"{change_pct:+.2f}%")

            with col2:
                st.metric("52W High", f"₹{w52['52w_high']:,.2f}", f"{w52['pct_from_high']}% away")

            with col3:
                st.metric("52W Low", f"₹{w52['52w_low']:,.2f}", f"{w52['pct_from_low']}% above")

            with col4:
                st.metric("RSI", f"{round(last['RSI'], 1)}")

            if spike:
                st.warning(f"⚡ Volume Spike — {ratio}x average volume")
            else:
                st.info(f"Volume: {int(last['Volume']):,} · Avg: {int(last['AvgVol20']):,} · {ratio}x average")

                st.caption(f"Signal: {signal}")

                st.divider()