import time
import json
import requests
import threading
import pandas as pd
import numpy as np
import math
import yfinance as yf
from datetime import datetime, timezone

def load_config():
    try:
        with open("config.json", "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return None

def smoothrng(x, t, m):
    wper = t * 2 - 1
    diff = x.diff().abs()
    avrng = diff.ewm(span=t, adjust=False).mean()
    smrng = avrng.ewm(span=wper, adjust=False).mean() * m
    return smrng

def rngfilt(x, r):
    filt = np.zeros(len(x))
    for i in range(len(x)):
        if i == 0:
            filt[i] = x.iloc[i]
            continue
        
        prev_filt = filt[i-1]
        curr_x = x.iloc[i]
        curr_r = r.iloc[i]
        
        if curr_x > prev_filt:
            val = curr_x - curr_r
            filt[i] = prev_filt if val < prev_filt else val
        elif curr_x + curr_r > prev_filt:
            filt[i] = prev_filt
        else:
            filt[i] = curr_x + curr_r
            
    return pd.Series(filt, index=x.index)

def calculate_range_filter(df, per=100, mult=3.0):
    src = df['Close']
    smrng = smoothrng(src, per, mult)
    filt = rngfilt(src, smrng)
    
    upward = np.zeros(len(src))
    downward = np.zeros(len(src))
    
    for i in range(1, len(src)):
        if filt.iloc[i] > filt.iloc[i-1]:
            upward[i] = upward[i-1] + 1
        elif filt.iloc[i] < filt.iloc[i-1]:
            upward[i] = 0
        else:
            upward[i] = upward[i-1]
            
        if filt.iloc[i] < filt.iloc[i-1]:
            downward[i] = downward[i-1] + 1
        elif filt.iloc[i] > filt.iloc[i-1]:
            downward[i] = 0
        else:
            downward[i] = downward[i-1]
            
    upward = pd.Series(upward, index=src.index)
    downward = pd.Series(downward, index=src.index)
    
    # rfupward := src > filt and src > src[1] and upward > 0 or src > filt and src < src[1] and upward > 0
    rfupward = (src > filt) & (src != src.shift(1)) & (upward > 0)
    rfdownward = (src < filt) & (src != src.shift(1)) & (downward > 0)
    
    return rfupward, rfdownward

def kernel_regression(src, h2=8.0, r=8.0, x_0=25):
    # Calculate fixed weights for the kernel
    weights = []
    # loop from 0 to size+x_0 (which is 1+25 = 26 in pine script since size of array.from(close) is 1)
    for i in range(x_0 + 2):
        w = math.pow(1 + (math.pow(i, 2) / ((math.pow(h2, 2) * 2 * r))), -r)
        weights.append(w)
        
    weights = np.array(weights)
    sum_w = np.sum(weights)
    
    # Reverse weights because rolling window returns [t-26, ..., t-1, t] 
    # but weight[0] applies to t, weight[1] applies to t-1
    reversed_weights = weights[::-1]
    
    def apply_kernel(x):
        if len(x) < len(reversed_weights):
            return np.nan
        return np.dot(x, reversed_weights) / sum_w

    return src.rolling(window=len(reversed_weights)).apply(apply_kernel, raw=True)

def calculate_rqk(df, h2=8.0, r=8.0, x_0=25, lag=2):
    src = df['Close']
    yhat1 = kernel_regression(src, h2, r, x_0)
    
    rqkuptrend = yhat1.shift(1) < yhat1
    rqkdowntrend = yhat1.shift(1) > yhat1
    
    return rqkuptrend, rqkdowntrend

def count_consecutive(series):
    streak = 0
    res = []
    for val in series:
        if val:
            streak += 1
        else:
            streak = 0
        res.append(streak)
    return pd.Series(res, index=series.index)

def main():
    print("DIY Strategy Alert Engine Started!")
    config = load_config()
    if not config:
        return
        
    tickers = config.get("diy_tickers", config.get("tickers", []))
    interval = config.get("interval", "5m")
    webhook_url = config.get("diy_google_sheets_webhook")
    
    if not webhook_url or "PASTE_YOUR_NEW" in webhook_url:
        print("Warning: diy_google_sheets_webhook not set in config.json")
    else:
        print("Connected to Google Sheets Webhook!")
    
    # Determine lookback period based on interval
    if interval.endswith("m"):
        period = "1mo"
    elif interval.endswith("h"):
        period = "1mo"
    else:
        period = "1y"
        
    # State tracking
    last_processed_time = {ticker: None for ticker in tickers}
    
    while True:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Scanning {len(tickers)} tickers for DIY signals...")
        
        for ticker in tickers:
            try:
                # Download historical data
                df = yf.download(ticker, period=period, interval=interval, progress=False)
                if df.empty or len(df) < 100:
                    continue
                    
                # Fix pandas multi-level columns if present
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                    
                # 1. Range Filter
                rfupward, rfdownward = calculate_range_filter(df)
                
                # 2. RQK
                rqkuptrend, rqkdowntrend = calculate_rqk(df)
                
                df['leadinglongcond'] = rfupward
                df['leadingshortcond'] = rfdownward
                
                df['longCond'] = df['leadinglongcond'] & rqkuptrend
                df['shortCond'] = df['leadingshortcond'] & rqkdowntrend
                
                df['leadinglong_count'] = count_consecutive(df['leadinglongcond'])
                df['leadingshort_count'] = count_consecutive(df['leadingshortcond'])
                
                df['longcond_withexpiry'] = df['longCond'] & (df['leadinglong_count'] <= 3)
                df['shortcond_withexpiry'] = df['shortCond'] & (df['leadingshort_count'] <= 3)
                
                # Calculate CondIni
                cond_ini = np.zeros(len(df))
                for i in range(1, len(df)):
                    if df['longcond_withexpiry'].iloc[i]:
                        cond_ini[i] = 1
                    elif df['shortcond_withexpiry'].iloc[i]:
                        cond_ini[i] = -1
                    else:
                        cond_ini[i] = cond_ini[i-1]
                        
                df['CondIni'] = cond_ini
                df['CondIni_prev'] = df['CondIni'].shift(1).fillna(0)
                
                df['longCondition'] = df['longcond_withexpiry'] & ((df['CondIni_prev'] == -1) | (df['CondIni_prev'] == 0))
                df['shortCondition'] = df['shortcond_withexpiry'] & ((df['CondIni_prev'] == 1) | (df['CondIni_prev'] == 0))
                
                # We strictly check the LATEST CLOSED CANDLE (iloc[-2]) to avoid repainting
                current = df.iloc[-2]
                current_time = df.index[-2]
                
                if last_processed_time[ticker] == current_time:
                    continue
                    
                is_bullish = current['longCondition']
                is_bearish = current['shortCondition']
                
                if is_bullish or is_bearish:
                    last_processed_time[ticker] = current_time
                    status_str = "BULLISH" if is_bullish else "BEARISH"
                    direction = "BULLISH (UP)" if is_bullish else "BEARISH (DOWN)"
                    
                    print(f"DIY SIGNAL: {ticker} is {direction} at {current_time}")
                    
                    # POST to Google Sheets
                    if webhook_url and webhook_url.startswith("http"):
                        payload = {
                            "ticker": ticker,
                            "status": status_str,
                            "price": float(current['Close']),
                            "time": str(current_time)
                        }
                        threading.Thread(target=lambda u=webhook_url, p=payload: requests.post(u, json=p)).start()
                        
            except Exception as e:
                print(f"Error processing {ticker}: {e}")
                
        # Sleep for 15 seconds
        time.sleep(15)

if __name__ == "__main__":
    main()
