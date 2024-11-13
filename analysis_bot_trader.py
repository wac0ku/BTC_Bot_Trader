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
def fetch_data(symbol='BTC/USDT', timeframe='1m', limit=500):
    ohlcv = binance.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    close_prices = [x[4] for x in ohlcv]  # Schlusskurse
    return np.array(close_prices)

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

# Einfache Trading-Logik basierend auf Fourier- und OU-Ergebnissen
def trading_strategy(symbol='BTC/USDT'):
    prices = fetch_data(symbol=symbol)
    
    # Fourier-Analyse durchführen
    frequencies, magnitude = fourier_analysis(prices)
    
    # Plot für Frequenzkomponenten
    plt.plot(frequencies, magnitude)
    plt.xlabel('Frequenzen')
    plt.ylabel('Magnitude')
    plt.title('Fourier-Spektralanalyse')
    plt.show()

    # Ornstein-Uhlenbeck-Analyse für Mean Reversion
    ou_prediction = ornstein_uhlenbeck(prices)
    current_price = prices[-1]
    
    # Trading-Entscheidungen basierend auf Mean Reversion
    if ou_prediction > current_price:
        print("Kauf-Signal: Preis wird möglicherweise steigen.")
        # binance.create_market_buy_order(symbol, 0.001) # Beispiel Kauf-Order
    elif ou_prediction < current_price:
        print("Verkauf-Signal: Preis wird möglicherweise fallen.")
        # binance.create_market_sell_order(symbol, 0.001) # Beispiel Verkaufs-Order
    else:
        print("Keine Aktion: Keine starken Signale.")
        
# Hauptschleife für den Trading Bot
def run_bot():
    while True:
        trading_strategy()
        time.sleep(60)  # 1 Minute warten, bevor die nächste Analyse durchgeführt wird

# Trading Bot starten
run_bot()
