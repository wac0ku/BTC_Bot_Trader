import logging
import numpy as np
import time

import ccxt
from scipy.fftpack import fft
import binance

# Create a logger
logger = logging.getLogger('trading_bot')
logger.setLevel(logging.INFO)

# Create a file handler and a stream handler
file_handler = logging.FileHandler('trading_bot.log')
stream_handler = logging.StreamHandler()

# Create a formatter and set it for the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)

# Add the handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

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
    try:
        ohlcv = binance.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        close_prices = [x[4] for x in ohlcv]  # Schlusskurse
        logger.info(f'Fetched data for {symbol} with timeframe {timeframe} and limit {limit}')
        return np.array(close_prices)
    except Exception as e:
        logger.error(f'Failed to fetch data: {e}')

# Bullish-Bearish Strategy
# Bollinger Bands berechnen
def calc_boll_bands(prices, window = 20, num_std_abw = 2):
    try:
        rolling_mean = np.mean(prices[-window:])
        rolling_std = np.std(prices[-window:])
        upper_band = rolling_mean + (rolling_std * num_std_abw)
        lower_band = rolling_mean - (rolling_std * num_std_abw)
        logger.info(f'Calculated Bollinger Bands for {len(prices)} prices')
        return rolling_mean, upper_band, lower_band
    except Exception as e:
        logger.error(f'Failed to calculate Bollinger Bands: {e}')

# Parabolic SAR berechnen
def calc_SAR(prices, initial_af=0.02, max_af=0.2):
    try:
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
        logger.info(f'Calculated Parabolic SAR for {len(prices)} prices')
        return parabolic_sar[-1]
    except Exception as e:
        logger.error(f'Failed to calculate Parabolic SAR: {e}')

# end Bullish-Bearish-strategy

# Fourier-Analyse zur Erkennung von Zyklen und Mustern
def fourier_analysis(prices):
    try:
        n = len(prices)
        prices_fft = fft(prices)
        frequencies = np.fft.fftfreq(n)
        logger.info(f'Performed Fourier analysis on {len(prices)} prices')
        return frequencies, np.abs(prices_fft)
    except Exception as e:
        logger.error(f'Failed to perform Fourier analysis: {e}')

# Ornstein-Uhlenbeck-Modell für Mean Reversion
def ornstein_uhlenbeck(prices, theta=0.1, mu=None, sigma=0.2):
    try:
        if mu is None:
            mu = np.mean(prices)
        drift = theta * (mu - prices[-1])  # Mean Reversion
        shock = sigma * np.random.normal()
        logger.info(f'Calculated Ornstein-Uhlenbeck model for {len(prices)} prices')
        return prices[-1] + drift + shock
    except Exception as e:
        logger.error(f'Failed to calculate Ornstein-Uhlenbeck model: {e}')

# Kauf Order
def buy(symbol):
    try:
        binance.create_market_buy_order(symbol, 0.001)
        logger.info(f'Placed buy order for {symbol}')
    except Exception as e:
        logger.error(f'Failed to place buy order: {e}')

# Verkauf Order
def sell(symbol):
    try:
        binance.create_market_sell_order(symbol, 0.001)
        logger.info(f'Placed sell order for {symbol}')
    except Exception as e:
        logger.error(f'Failed to place sell order: {e}')

# Funktion zur Auswahl der Strategie
def select_strat(prices):
    try:
        # Trend vorhanden, wenn short SMA > long SMA
        short_sma = np.mean(prices[-50:]) # 50-Tage-SMA
        long_sma = np.mean(prices[-200:]) # 200-Tage-SMA
        if short_sma > long_sma:
            logger.info('Selected trend-following strategy')
            return "trend-following"
        else:
            logger.info('Selected mean-reversion strategy')
            return "mean-reversion"
    except Exception as e:
        logger.error(f'Failed to select strategy: {e}')

# Einfache Trading-Logik basierend auf Fourier- und OU-Ergebnissen
def trading_strategy(btc_usdt='BTC/USDT'):
    try:
        prices = fetch_data(symbol=btc_usdt)
        current_price = prices[-1]

        # Strategie auswählen
        strategy = select_strat(prices)
        logger.info(f'Selected strategy: {strategy}')

        if strategy == "trend-following":
            # Calculate Bollinger Bands + SAR
            rolling_mean, upper_band, lower_band = calc_boll_bands(prices)
            sar_val = calc_SAR(prices)

            if current_price < lower_band and current_price > sar_val:
                logger.info(f'Buy signal for {btc_usdt} at {current_price}')
                buy(btc_usdt)
            elif current_price > upper_band and current_price < sar_val:
                logger.info(f'Sell signal for {btc_usdt} at {current_price}')
                sell(btc_usdt)
        
        elif strategy == "mean-reversion":
            # Fourier-Analyse und OU-Modell
            frequencies, magnitude = fourier_analysis(prices)
            ou_prediction = ornstein_uhlenbeck(prices)

            if ou_prediction > current_price:
                logger.info(f'Buy signal for {btc_usdt} at {current_price}')
                buy(btc_usdt)
            elif ou_prediction < current_price:
                logger.info(f'Sell signal for {btc_usdt} at {current_price}')
                sell(btc_usdt)
    except Exception as e:
        logger.error(f'Failed to execute trading strategy: {e}')

# Hauptschleife für den Trading Bot
def run_bot():
    while True:
        try:
            trading_strategy()
            logger.info('Trading strategy executed successfully')
        except Exception as e:
            logger.error(f'Failed to execute trading strategy: {e}')
        time.sleep(300)  # 5 Minute warten, bevor die nächste Analyse durchgeführt wird

# Trading Bot starten
run_bot()