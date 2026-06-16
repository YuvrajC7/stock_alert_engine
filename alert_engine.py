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

def run_engine():
    config = load_config()
    tickers = config.get("tickers", ["AAPL"])
    interval = config.get("interval", "5m")
    
    print(f"[{datetime.now()}] Starting HIGH-SPEED Alert Engine for {len(tickers)} tickers on {interval} interval...")
    
    # Keep track of last alerts to avoid spamming the same candle window
    last_alert_time = {ticker: None for ticker in tickers}
    
    while True:
        try:
            # We use bulk download to fetch all 50 stocks simultaneously. This reduces scan time from 50s to ~2s.
            tickers_str = " ".join(tickers)
            df_bulk = yf.download(tickers_str, period="5d", interval=interval, group_by="ticker", threads=True, progress=False)
            
            for ticker in tickers:
                try:
                    if len(tickers) == 1:
                        df = df_bulk.dropna()
                    else:
                        if ticker not in df_bulk.columns.levels[0]:
                            continue
                        df = df_bulk[ticker].dropna()
                        
                    if df.empty or len(df) < 65:
                        continue
                        
                    # Apply SSL logic
                    df = apply_ssl_hybrid(df.copy())
                    
                    # We strictly check the LATEST CLOSED CANDLE (iloc[-2]) to avoid repainting/fake arrows
                    current = df.iloc[-2]
                    current_time = df.index[-2]
                    
                    # If we already alerted for this specific 5-minute window, don't spam.
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
                        
                        # Record the time so we only send 1 alert per 5m candle
                        last_alert_time[ticker] = current_time
                        
                except Exception as e:
                    pass # Ignore individual ticker errors to keep the loop fast
                    
        except Exception as e:
            print(f"[{datetime.now()}] Error fetching bulk data: {e}")
            
        # Sleep for only 15 seconds (instead of 60) for near-instant detection
        time.sleep(15)

if __name__ == "__main__":
    run_engine()
