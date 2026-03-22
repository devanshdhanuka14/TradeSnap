import streamlit as st
from data import fetch_stock_data, compute_indicators, is_volume_spike, get_signal, get_52w_position, fetch_news
from concurrent.futures import ThreadPoolExecutor, as_completed

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
        value="RELIANCE.NS\nHDFCBANK.NS\nTCS.NS",
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

import plotly.graph_objects as go
from plotly.subplots import make_subplots

def build_chart(df, ticker):
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3]
    )

    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="Price"
        ),
        row=1, col=1
    )

    fig.add_trace(
        go.Scatter(x=df.index, y=df["MA20"], name="MA20", line=dict(color="blue", width=1.5)),
        row=1, col=1
    )

    fig.add_trace(
        go.Scatter(x=df.index, y=df["MA50"], name="MA50", line=dict(color="orange", width=1.5)),
        row=1, col=1
    )

    fig.add_trace(
        go.Bar(x=df.index, y=df["Volume"], name="Volume", marker_color="gray"),
        row=2, col=1
    )

    fig.update_layout(
        title=ticker,
        xaxis_rangeslider_visible=False,
        height=500,
        hovermode="x unified"
    )

    return fig

if run:
    if not tickers:
        st.error("Please enter at least one ticker.")
    else:
        snapshot = []

        def fetch_all(ticker):
            df_chart, df_1y, company_name = fetch_stock_data(ticker, chart_period)
            return ticker, df_chart, df_1y, company_name

        with st.spinner("Fetching data for all stocks..."):
            with ThreadPoolExecutor() as executor:
                futures = {executor.submit(fetch_all, ticker): ticker for ticker in tickers}
                results = {}
                for future in as_completed(futures):
                    ticker, df_chart, df_1y, company_name = future.result()
                    results[ticker] = (df_chart, df_1y, company_name)

        for ticker in tickers:
            df_chart, df_1y, company_name = results[ticker]

            if df_chart is None:
                st.warning(f"Could not fetch data for {ticker}. Check the ticker symbol.")
                continue

            df_chart = compute_indicators(df_chart)

            spike, ratio = is_volume_spike(df_chart, vol_threshold)
            verdict, trend, reasoning = get_signal(df_chart)
            w52 = get_52w_position(df_1y)

            last = df_chart.iloc[-1]
            prev_close = df_chart.iloc[-2]["Close"]
            price = last["Close"]
            change = price - prev_close
            change_pct = (change / prev_close) * 100

            # Header
            st.markdown(
                f"""
                <div style="padding: 14px 18px; border-radius: 8px; background: linear-gradient(90deg, #1a1a2e, #16213e); border-left: 5px solid #00d4ff;">
                    <span style="color: #00d4ff; font-size: 22px; font-weight: bold;">{ticker}</span>
                    <span style="color: #aaaaaa; font-size: 15px; margin-left: 12px;">{company_name}</span>
                </div>
                """,
                unsafe_allow_html=True
            )
            st.markdown("<br>", unsafe_allow_html=True)

            # Metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Price", f"₹{price:,.2f}", f"{change_pct:+.2f}%")
            with col2:
                st.metric("52W High", f"₹{w52['52w_high']:,.2f}", f"{w52['pct_from_high']}% away")
            with col3:
                st.metric("52W Low", f"₹{w52['52w_low']:,.2f}", f"{w52['pct_from_low']}% above")
            with col4:
                st.metric("RSI", f"{round(last['RSI'], 1)}")

            # Volume
            if spike:
                st.warning(f"⚡ Volume Spike — {ratio}x average volume")
            else:
                st.info(f"Volume: {int(last['Volume']):,} · Avg: {int(last['AvgVol20']):,} · {ratio}x average")

            # Signal
            if "BUY" in verdict or "BULLISH" in verdict:
                signal_color = "green"
            elif "SELL" in verdict or "BEARISH" in verdict:
                signal_color = "red"
            else:
                signal_color = "orange"

            st.markdown(
                f"""
                <div style="padding: 12px 16px; border-radius: 8px; border-left: 4px solid {signal_color}; background-color: #1a1a1a;">
                    <span style="color: {signal_color}; font-weight: bold; font-size: 16px;">{verdict}</span><br>
                    <span style="color: #aaaaaa; font-size: 13px;">{trend}</span><br>
                    <span style="color: #cccccc; font-size: 13px; margin-top: 4px;">{reasoning}</span>
                </div>
                """,
                unsafe_allow_html=True
            )

            # Chart
            fig = build_chart(df_chart, ticker)
            st.plotly_chart(fig, use_container_width=True)

            with st.expander(f"📰 Top Headlines — {ticker}"):
                articles = fetch_news(ticker)
                if not articles:
                    st.markdown(
                        """
                        <div style="padding: 12px; color: #aaaaaa; font-size: 13px;">
                            No headlines found for this stock.
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                else:
                    for article in articles:
                        st.markdown(
                            f"""
                            <div style="padding: 12px 16px; margin-bottom: 10px; border-radius: 8px; 
                                        background-color: #1a1a2e; border-left: 3px solid #00d4ff;">
                                <a href="{article['url']}" target="_blank" 
                                style="color: #ffffff; font-size: 14px; font-weight: 500; 
                                        text-decoration: none; line-height: 1.5;">
                                    {article['title']}
                                </a>
                                <div style="margin-top: 6px; color: #888888; font-size: 11px;">
                                    {article['source']} · {article['publishedAt']}
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

            # Snapshot row
            snapshot.append({
                "Company": company_name,
                "Ticker": ticker,
                "Price": round(price, 2),
                "Change%": round(change_pct, 2),
                "RSI": round(last["RSI"], 1),
                "MA20": round(last["MA20"], 2),
                "MA50": round(last["MA50"], 2),
                "Volume": int(last["Volume"]),
                "AvgVol20": int(last["AvgVol20"]),
                "VolumeSpike": spike,
                "SpikeRatio": ratio,
                "52W_High": w52["52w_high"],
                "52W_Low": w52["52w_low"],
                "52W_Position%": w52["position_pct"],
                "Signal": verdict,
            })

            st.divider()

        if snapshot:
            import pandas as pd
            df_snapshot = pd.DataFrame(snapshot)
            csv = df_snapshot.to_csv(index=False)

            st.download_button(
            label="⬇ Export Snapshot as CSV",
            data=csv,
            file_name=f"tradesnap_snapshot.csv",
            mime="text/csv"
            )

        