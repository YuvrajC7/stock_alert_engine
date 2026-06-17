import yfinance as yf
import pandas as pd
import time
from datetime import datetime
import json
from ssl_hybrid import apply_ssl_hybrid
from notifier import send_desktop_notification, send_email

def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)

def resample_custom(df, target_interval_minutes):
    """
    Takes 15m data and perfectly stitches it into 30m or 60m candles starting at 09:15.
    This fixes the Yahoo Finance misalignment bug for Indian markets.
    """
    shifted = df.copy()
    shift_mins = target_interval_minutes - 15
    shifted.index = shifted.index + pd.Timedelta(minutes=shift_mins)
    
    resampled = shifted.resample(f'{target_interval_minutes}min').agg({
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last',
        'Volume': 'sum'
    }).dropna()
    
    resampled.index = resampled.index - pd.Timedelta(minutes=shift_mins)
    return resampled

def run_engine():
    config = load_config()
    tickers = config.get("tickers", ["AAPL"])
    interval = config.get("interval", "5m")
    
    # Determine lookback period based on interval to ensure we have enough candles (minimum 65)
    if interval in ["1m", "2m", "5m"]:
        period_str = "5d"
    elif interval in ["15m", "30m", "60m", "90m", "1h"]:
        period_str = "1mo"
    else:
        period_str = "1y"
        
    fetch_interval = interval
    resample_minutes = None
    
    # If the user wants 30m or 60m, we fetch perfectly aligned 15m data and stitch it together.
    if interval == "30m":
        fetch_interval = "15m"
        resample_minutes = 30
    elif interval in ["1h", "60m"]:
        fetch_interval = "15m"
        resample_minutes = 60
        
    print(f"[{datetime.now()}] Starting HIGH-SPEED Alert Engine for {len(tickers)} tickers on {interval} interval (Period: {period_str})...")
    if resample_minutes:
        print(f"[*] Engine is actively resampling perfectly aligned {interval} candles from {fetch_interval} base data.")
    
    # Keep track of last alerts to avoid spamming the same candle window
    last_alert_time = {ticker: None for ticker in tickers}
    
    while True:
        try:
            # We use bulk download to fetch all stocks simultaneously.
            tickers_str = " ".join(tickers)
            df_bulk = yf.download(tickers_str, period=period_str, interval=fetch_interval, group_by="ticker", threads=True, progress=False)
            
            for ticker in tickers:
                try:
                    if len(tickers) == 1:
                        df = df_bulk.dropna()
                    else:
                        if ticker not in df_bulk.columns.levels[0]:
                            continue
                        df = df_bulk[ticker].dropna()
                    
                    if df.empty:
                        continue
                        
                    # Stitch the 15m candles into perfectly aligned 30m/60m candles if needed
                    if resample_minutes:
                        df = resample_custom(df, resample_minutes)
                        
                    if df.empty or len(df) < 65:
                        continue
                        
                    # Apply SSL logic
                    df = apply_ssl_hybrid(df.copy())
                    
                    # We strictly check the LATEST CLOSED CANDLE (iloc[-2]) to avoid repainting/fake arrows
                    current = df.iloc[-2]
                    current_time = df.index[-2]
                    
                    # If we already alerted for this specific candle window, don't spam.
                    if last_alert_time[ticker] == current_time:
                        continue 
                        
                    is_bullish = current['Alert_Bullish']
                    is_bearish = current['Alert_Bearish']
                    
                    if is_bullish or is_bearish:
                        direction = "BULLISH (UP)" if is_bullish else "BEARISH (DOWN)"
                        title = f"SSL Hybrid Alert: {ticker} {direction}"
                        message = f"{ticker} has fired an INSTANT {direction} signal on {interval} chart at {current['Close']:.2f} (Time: {current_time})."
                        
                        print(f"\n[{datetime.now()}] ⚡ FAST ALERT TRIGGERED: {title}")
                        send_desktop_notification(title, message)
                        send_email(title, message)
                        
                        # Record the time so we only send 1 alert per candle
                        last_alert_time[ticker] = current_time
                        
                except Exception as e:
                    pass # Ignore individual ticker errors to keep the loop fast
                    
        except Exception as e:
            print(f"[{datetime.now()}] Error fetching bulk data: {e}")
            
        # Sleep for only 15 seconds for near-instant detection when the candle closes
        time.sleep(15)

if __name__ == "__main__":
    run_engine()
