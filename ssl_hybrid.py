import pandas as pd
import pandas_ta as ta
import numpy as np

def calculate_hma(series, length):
    """
    HMA(src, len) = WMA(2 * WMA(src, len / 2) - WMA(src, len), round(sqrt(len)))
    """
    half_length = int(length / 2)
    sqrt_length = int(np.round(np.sqrt(length)))
    
    wmaf = ta.wma(series, length=half_length)
    wmas = ta.wma(series, length=length)
    
    # 2 * WMA(len/2) - WMA(len)
    diff = (2 * wmaf) - wmas
    
    # WMA of the diff with sqrt(len)
    hma = ta.wma(diff, length=sqrt_length)
    return hma

def apply_ssl_hybrid(df):
    """
    Applies the SSL Hybrid (HMA baseline, HMA exit) logic to a OHLCV DataFrame.
    Returns the DataFrame with additional columns indicating alerts.
    """
    close = df['Close']
    high = df['High']
    low = df['Low']
    
    # === BASELINE SETTINGS ===
    len_baseline = 60
    multy = 0.2
    
    # === EXIT SETTINGS ===
    len3 = 15
    
    # Calculate True Range
    df['TR'] = ta.true_range(high, low, close)
    
    # BASELINE CALCULATIONS
    # BBMC = ma(HMA, close, 60)
    # Keltma = ma(HMA, close, 60)
    # rangema = ta.ema(rangeValue, 60)
    df['BBMC'] = calculate_hma(close, len_baseline)
    df['Keltma'] = calculate_hma(close, len_baseline)
    df['rangema'] = ta.ema(df['TR'], length=len_baseline)
    
    df['upperk'] = df['Keltma'] + df['rangema'] * multy
    df['lowerk'] = df['Keltma'] - df['rangema'] * multy
    
    # EXIT VALUES
    # ExitHigh = ma(HMA, high, 15)
    # ExitLow = ma(HMA, low, 15)
    df['ExitHigh'] = calculate_hma(high, len3)
    df['ExitLow'] = calculate_hma(low, len3)
    
    # Hlv3 Calculation
    hlv3 = np.zeros(len(df))
    # Handling NaN cases gracefully
    exit_high = df['ExitHigh'].fillna(0).values
    exit_low = df['ExitLow'].fillna(0).values
    close_vals = close.values
    
    for i in range(1, len(df)):
        if close_vals[i] > exit_high[i]:
            hlv3[i] = 1
        elif close_vals[i] < exit_low[i]:
            hlv3[i] = -1
        else:
            hlv3[i] = hlv3[i-1]
            
    df['Hlv3'] = hlv3
    
    # sslExit = Hlv3 < 0 ? ExitHigh : ExitLow
    df['sslExit'] = np.where(df['Hlv3'] < 0, df['ExitHigh'], df['ExitLow'])
    
    # === SIGNAL CALCULATIONS ===
    # base_cross_Long = ta.crossover(close, sslExit)
    # base_cross_Short = ta.crossunder(close, sslExit)
    
    # Crossover logic
    df['close_prev'] = close.shift(1)
    df['sslExit_prev'] = df['sslExit'].shift(1)
    
    df['base_cross_Long'] = (close > df['sslExit']) & (df['close_prev'] <= df['sslExit_prev'])
    df['base_cross_Short'] = (close < df['sslExit']) & (df['close_prev'] >= df['sslExit_prev'])
    
    # === COLOR LOGIC ===
    # baseline_color = close > upperk ? bullish_color : close < lowerk ? bearish_color : neutral_color
    
    df['baseline_bullish'] = close > df['upperk']
    df['baseline_bearish'] = close < df['lowerk']
    
    # === FINAL ALERTS ===
    # Arrow matches broad line
    df['Alert_Bullish'] = df['base_cross_Long'] & df['baseline_bullish']
    df['Alert_Bearish'] = df['base_cross_Short'] & df['baseline_bearish']
    
    return df
