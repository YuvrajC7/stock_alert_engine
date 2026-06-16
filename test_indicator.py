import yfinance as yf
import pandas as pd
from ssl_hybrid import apply_ssl_hybrid

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

ticker = "NVDA"
print(f"--- Running Live Data Test for {ticker} ---")
df = yf.Ticker(ticker).history(period="5d", interval="5m")

if df.empty:
    print("No data fetched. Market might be closed or ticker is wrong.")
else:
    df = apply_ssl_hybrid(df)
    
    cols_to_show = ['Close', 'BBMC', 'upperk', 'lowerk', 'sslExit', 'Alert_Bullish', 'Alert_Bearish']
    print("\n[Latest 5 Candles]")
    print(df[cols_to_show].tail(5))
    
    bullish_alerts = df[df['Alert_Bullish'] == True]
    bearish_alerts = df[df['Alert_Bearish'] == True]
    
    print(f"\n[Summary for last 5 Days]")
    print(f"Total Bullish Alerts generated: {len(bullish_alerts)}")
    print(f"Total Bearish Alerts generated: {len(bearish_alerts)}")
    
    if not bullish_alerts.empty:
        print("\n[Most Recent Bullish Alert Time & Details]")
        print(bullish_alerts[cols_to_show].tail(1))
        
    if not bearish_alerts.empty:
        print("\n[Most Recent Bearish Alert Time & Details]")
        print(bearish_alerts[cols_to_show].tail(1))

print("\n--- Test Completed Successfully ---")
