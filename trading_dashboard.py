import pandas as pd
import numpy as np
import requests
import time
import streamlit as st

def fetch_kucoin_data(symbol='BTC-USDT', interval='5min', limit=100):
    url = f'https://api.kucoin.com/api/v1/market/candles?symbol={symbol}&type={interval}&limit={limit}'
    response = requests.get(url)
    data = response.json()['data']
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'close', 'high', 'low', 'volume', 'turnover'])
    df = df.astype(float)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
    return df[::-1].reset_index(drop=True)  # Reverse to chronological order

def calculate_rsi(data, period=7):
    delta = data['close'].diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_gain = pd.Series(gain).rolling(window=period, min_periods=1).mean()
    avg_loss = pd.Series(loss).rolling(window=period, min_periods=1).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_volume_oscillator(data, short_length=1, long_length=5):
    sma_long = data['volume'].rolling(window=long_length, min_periods=1).mean()
    return ((data['volume'] - sma_long) / sma_long) * 100

def calculate_adx(data, period=14):
    tr = np.maximum(data['high'] - data['low'], 
                    np.maximum(abs(data['high'] - data['close'].shift(1)), 
                               abs(data['low'] - data['close'].shift(1))))
    atr = pd.Series(tr).rolling(window=period, min_periods=1).mean()
    
    plus_dm = np.where((data['high'] > data['high'].shift(1)) & (data['high'] - data['high'].shift(1) > data['low'].shift(1) - data['low']), data['high'] - data['high'].shift(1), 0)
    minus_dm = np.where((data['low'].shift(1) > data['low']) & (data['low'].shift(1) - data['low'] > data['high'] - data['high'].shift(1)), data['low'].shift(1) - data['low'], 0)
    
    plus_di = 100 * pd.Series(plus_dm).rolling(window=period, min_periods=1).mean() / atr
    minus_di = 100 * pd.Series(minus_dm).rolling(window=period, min_periods=1).mean() / atr
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = pd.Series(dx).rolling(window=period, min_periods=1).mean()
    return adx

def generate_signals(data):
    data['RSI'] = calculate_rsi(data)
    data['VO'] = calculate_volume_oscillator(data)
    data['ADX'] = calculate_adx(data)
    
    bullish_condition = (data['VO'] >= 55) & (data['RSI'] <= 25) & (data['close'] < data['open']) & (data['ADX'] > 20)
    bearish_condition = (data['VO'] >= 55) & (data['RSI'] >= 50) & (data['close'] > data['open']) & (data['ADX'] > 20)
    
    data['Signal'] = np.where(bullish_condition, 'Bullish', np.where(bearish_condition, 'Bearish', 'Neutral'))
    return data[['timestamp', 'close', 'RSI', 'VO', 'ADX', 'Signal']]

def analyze_market(data):
    bullish_count = (data['Signal'] == 'Bullish').sum()
    bearish_count = (data['Signal'] == 'Bearish').sum()
    
    if bullish_count > bearish_count:
        return "Market shows bullish momentum. Consider buying opportunities with caution."
    elif bearish_count > bullish_count:
        return "Market indicates bearish pressure. Consider selling or avoiding long positions."
    else:
        return "Market is neutral. No strong trends detected."

st.title("KuCoin Market Analysis")

symbol = st.text_input("Enter Trading Pair (e.g., BTC-USDT):", "BTC-USDT")
timeframes = ['5min', '15min', '30min', '1hour', '4hour']

for tf in timeframes:
    df = fetch_kucoin_data(symbol=symbol, interval=tf)
    df_signals = generate_signals(df)
    analysis = analyze_market(df_signals)
    
    st.subheader(f"Timeframe: {tf}")
    st.write(analysis)
    st.dataframe(df_signals.tail(10))
