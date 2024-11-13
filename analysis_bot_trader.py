import logging
import time
import numpy as np
import ccxt
from scipy.fftpack import fft

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

class TradingBot:
    def __init__(self, api_key, api_secret, symbol='BTC/USDT'):
        self.binance = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True
        })
        self.symbol = symbol

    def fetch_data(self, timeframe='1h', limit=500):
        try:
            ohlcv = self.binance.fetch_ohlcv(self.symbol, timeframe=timeframe, limit=limit)
            close_prices = [x[4] for x in ohlcv]
            logger.info(f'Fetched data for {self.symbol} with timeframe {timeframe} and limit {limit}')
            return np.array(close_prices)
        except Exception as e:
            logger.error(f'Failed to fetch data for {self.symbol}: {str(e)}')
            return None

    def validate_data(self, prices):
        if prices is None or len(prices) == 0:
            logger.error('No prices available for validation.')
            return False
        if np.any(np.isnan(prices)):
            logger.error('Prices contain NaN values.')
            return False
        return True

    def fetch_sar(self):
        try:
            params = {"indicator": "sar"}
            sar_data = self.binance.fetch_ta_indicator(self.symbol, params=params)
            logger.info(f'Fetched SAR data for {self.symbol}')
            return sar_data['value'][-1]
        except Exception as e:
            logger.error(f'Failed to fetch SAR data for {self.symbol}: {str(e)}')
            return None

    def calculate_bollinger_bands(self, prices, window=20, num_std_dev=2):
        try:
            rolling_mean = np.mean(prices[-window:])
            rolling_std = np.std(prices[-window:])
            upper_band = rolling_mean + (rolling_std * num_std_dev)
            lower_band = rolling_mean - (rolling_std * num_std_dev)
            logger.info(f'Calculated Bollinger Bands for prices with window {window} and num_std_dev {num_std_dev}')
            return rolling_mean, upper_band, lower_band
        except Exception as e:
            logger.error(f'Failed to calculate Bollinger Bands: {str(e)}')
            return None, None, None

    def calculate_rsi(self, prices, period=14):
        delta = np.diff(prices)
        gain = (delta[delta > 0]).mean()
        loss = (-delta[delta < 0]).mean()
        rs = gain / loss if loss != 0 else 0
        rsi = 100 - (100 / (1 + rs))
        logger.info(f'Calculated RSI: {rsi}')
        return rsi

    def fourier_analysis(self, prices):
        try:
            n = len(prices)
            prices_fft = fft(prices)
            frequencies = np.fft.fftfreq(n)
            magnitude = np.abs(prices_fft)
            logger.info(f'Performed Fourier analysis for prices')
            return frequencies, magnitude
        except Exception as e:
            logger.error(f'Failed to perform Fourier analysis: {str(e)}')
            return None, None

    def ornstein_uhlenbeck(self, prices, theta=0.1, mu=None, sigma=0.2):
        try:
            if mu is None:
                mu = np.mean(prices)
            drift = theta * (mu - prices[-1])
            shock = sigma * np.random.normal()
            logger.info(f'Calculated Ornstein-Uhlenbeck model for prices with theta {theta}, mu {mu}, and sigma {sigma}')
            return prices[-1] + drift + shock
        except Exception as e:
            logger.error(f'Failed to calculate Orn stein-Uhlenbeck model: {str(e)}')
            return None

    def buy(self, amount):
        try:
            order = self.binance.create_market_buy_order(self.symbol, amount)
            logger.info(f'Executed buy order: {order}')
            return order
        except Exception as e:
            logger.error(f'Failed to execute buy order: {str(e)}')
            return None

    def sell(self, amount):
        try:
            order = self.binance.create_market_sell_order(self.symbol, amount)
            logger.info(f'Executed sell order: {order}')
            return order
        except Exception as e:
            logger.error(f'Failed to execute sell order: {str(e)}')
            return None

    def trading_strategy(self):
        try:
            prices = self.fetch_data()
            
            if not self.validate_data(prices):
                return  # Beende die Funktion, wenn die Daten ungültig sind

            current_price = prices[-1]
            rsi = self.calculate_rsi(prices)
            
            # Strategie auswählen
            strategy = self.select_strategy(prices)
            logger.info(f'Selected strategy: {strategy}')

            # ATR für dynamisches Stop-Loss
            atr_value = self.calculate_atr(prices)

            if strategy == "trend_following":
                rolling_mean, upper_band, lower_band = self.calculate_bollinger_bands(prices)
                sar_value = self.fetch_sar()
                imbalance = self.analyze_order_book()

                # Kauf-/Verkaufssignale für Trendfolge
                if current_price < lower_band and current_price > sar_value and imbalance > 0 and rsi < 30:
                    logger.info(f'Generated buy signal for trend following strategy')
                    self.buy(amount=1)  # Beispielbetrag
                    stop_loss = self.set_stop_loss(current_price, atr_value, direction="long")

                elif current_price > upper_band and current_price < sar_value and imbalance < 0 and rsi > 70:
                    logger.info(f'Generated sell signal for trend following strategy')
                    self.sell(amount=1)  # Beispielbetrag
                    stop_loss = self.set_stop_loss(current_price, atr_value, direction="short")

            elif strategy == "mean_reversion":
                frequencies, magnitude = self.fourier_analysis(prices)
                ou_prediction = self.ornstein_uhlenbeck(prices)

                # Kauf-/Verkaufssignale für Mean Reversion
                if ou_prediction > current_price and rsi < 30:
                    logger.info(f'Generated buy signal for mean reversion strategy')
                    self.buy(amount=1)  # Beispielbetrag
                    stop_loss = self.set_stop_loss(current_price, atr_value, direction="long")

                elif ou_prediction < current_price and rsi > 70:
                    logger.info(f'Generated sell signal for mean reversion strategy')
                    self.sell(amount=1)  # Beispielbetrag
                    stop_loss = self.set_stop_loss(current_price, atr_value, direction="short")
        except Exception as e:
            logger.error(f'Failed to execute trading strategy: {str(e)}')

    def print_dashboard(self):
        logger.info("---- Dashboard ----")

# Hauptschleife
if __name__ == "__main__":
    api_key = 'YOUR_API_KEY'
    api_secret = 'YOUR_API_SECRET'
    bot = TradingBot(api_key, api_secret)

    while True:
        bot.trading_strategy()
        bot.print_dashboard()
        time.sleep(60)  # Wartezeit zwischen den Handelszyklen