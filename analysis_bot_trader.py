import ccxt
import numpy as np
from scipy.fftpack import fft
from scipy import stats
import matplotlib.pyplot as plt
import time

# Verbindung zur Binance-API herstellen
api_key = 'YOUR_API_KEY'
api_secret = 'YOUR_API_SECRET'
binance = ccxt.binance({
    'apiKey': api_key,
    'secret': api_secret,
    'enableRateLimit': True
})

# Funktion, um Marktdaten zu holen
def fetch_data(symbol='BTC/USDT', timeframe='5m', limit=500):
    ohlcv = binance.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    close_prices = [x[4] for x in ohlcv]  # Schlusskurse
    return np.array(close_prices)

# Bullish-Bearish Strategy
# Bollinger Bands berechnen
def calc_boll_bands(prices, window = 20, num_std_abw = 2):
    rolling_mean = np.mean(prices[-window:])
    rolling_std = np.std(prices[-window:])
    upper_band = rolling_mean + (rolling_std * num_std_abw)
    lower_band = rolling_mean - (rolling_std * num_std_abw)
    return rolling_mean, upper_band, lower_band

# Parabolic SAR berechnen
def calc_SAR(prices, initial_af=0.02, max_af=0.2):
    af = initial_af
    sar = prices[0]
    ep = prices[0]
    long_position = True
    parabolic_sar = []

    for i in range(1, len(prices)):
        sar += af * (ep - sar)
        if long_position:
            if prices[i] > ep:
                ep = prices[i]
                af = min(af + initial_af, max_af)
            if prices[i] < sar:
                long_position = False
                sar = ep
                af = initial_af
        else:
            if prices[i] < ep:
                ep = prices[i]
                af = min(af + initial_af, max_af)
            if prices[i] > sar:
                long_position = True
                sar = ep
                af = initial_af
        parabolic_sar.append(sar)
    return parabolic_sar[-1]

# end Bullish-Bearish-strategy

# Fourier-Analyse zur Erkennung von Zyklen und Mustern
def fourier_analysis(prices):
    n = len(prices)
    prices_fft = fft(prices)
    frequencies = np.fft.fftfreq(n)
    return frequencies, np.abs(prices_fft)

# Ornstein-Uhlenbeck-Modell für Mean Reversion
def ornstein_uhlenbeck(prices, theta=0.1, mu=None, sigma=0.2):
    if mu is None:
        mu = np.mean(prices)
    drift = theta * (mu - prices[-1])  # Mean Reversion
    shock = sigma * np.random.normal()
    return prices[-1] + drift + shock

# Kauf Order
def buy(symbol):
    binance.create_market_buy_order(symbol, 0.001)

def sell(symbol):
    binance.create_market_sell_order(symbol, 0.001)

# Funktion zur Auswahl der Strategie
def select_strat(prices):
    # Trend vorhanden, wenn short SMA > long SMA
    short_sma = np.mean(prices[-50:]) # 50-Tage-SMA
    long_sma = np.mean(prices[-200:]) # 200-Tage-SMA
    if short_sma > long_sma:
        return "trend-following"
    else:
        return "mean-reversion"

# Einfache Trading-Logik basierend auf Fourier- und OU-Ergebnissen
def trading_strategy(btc_usdt='BTC/USDT'):
    prices = fetch_data(symbol=btc_usdt)
    current_price = prices[-1]

    # Strategie auswählen
    strategy = select_strat(prices)
    print(f"Current Strategy: {strategy}")

    if strategy == "trend-following":
        # Calculate Bollinger Bands + SAR
        rolling_mean, upper_band, lower_band = calc_boll_bands(prices)
        sar_val = calc_SAR(prices)

        if current_price < lower_band and current_price > sar_val:
            print(f"Kaufe 0.001 BTC zu {current_price} USDT (trend-following)")
            buy(btc_usdt)
        elif current_price > upper_band and current_price < sar_val:
            print(f"Verkaufe 0.001 BTC zu {current_price} USDT (trend-following)")
            sell(btc_usdt)
    
    elif strategy == "mean-reversion":
        # Fourier-Analyse und OU-Modell
        frequencies, magnitude = fourier_analysis(prices)
        ou_prediction = ornstein_uhlenbeck(prices)

        if ou_prediction > current_price:
            print(f"Kaufe 0.001 BTC zu {current_price} USDT (mean-reversion)")
            buy(btc_usdt)
        elif ou_prediction < current_price:
            print(f"Verkaufe 0.001 BTC zu {current_price} USDT (mean-reversion)")
            sell(btc_usdt)
        

# Hauptschleife für den Trading Bot
def run_bot():
    while True:
        trading_strategy()
        time.sleep(300)  # 5 Minute warten, bevor die nächste Analyse durchgeführt wird

# Trading Bot starten
run_bot()
