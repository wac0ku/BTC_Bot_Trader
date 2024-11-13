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
    def __init__(self, api_key, api_secret, symbol='BTC/USDT', risk_percentage=0.015):
        self.binance = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True
        })
        self.symbol = symbol
        self.risk_percentage = risk_percentage
    
    def fetch_balance(self):
        """
        Zeigt Trading Balance an.

        :return balance: Balance in USDT
        """
        try:
            balance = self.binance.fetch_balance()
            return balance['total']['USDT']
        except Exception as e:
            logger.error(f"Failed to fetch balance: {str(e)}")
            return 0

    def calculate_trade_amount(self):
        balance = self.fetch_balance()
        amount = balance * self.risk_percentage
        logger.info(f"Calculated trade amount: {amount} USDT based on balance: {balance} USDT")
        return amount

    def fetch_data(self, timeframe='5m', limit=500):
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

    def fetch_indicator(self, indicator):
        try:
            params = {"indicator": indicator}
            data = self.binance.fetch_ta_indicator(self.symbol, params=params)
            logger.info(f"Fetched {indicator} data for {self.symbol}")
            return data['value'][-1]
        except Exception as e:
            logger.error(f"Failed to fetch {indicator} data for {self.symbol}: {str(e)}")
            return None

    def calculate_rsi(self, prices, period=14):
        delta = np.diff(prices)
        gain = (delta[delta > 0]).mean()
        loss = (-delta[delta < 0]).mean()
        rs = gain / loss if loss != 0 else 0
        rsi = 100 - (100 / (1 + rs))
        logger.info(f'Calculated RSI: {rsi}')
        return rsi

    def execute_order(self, order_type, amount):
        try:
            if order_type == 'buy':
                order = self.binance.place_market_buy_order(self.symbol, amount)
            elif order_type == 'sell':
                order = self.binance.place_market_sell_order(self.symbol, amount)
                logger.info(f'Executed {order_type} order: {order}')
        except Exception as e:
            logger.error(f"Failed to execute {order_type} order: {str(e)}")
            return None
    
    def check_buy_signal(self, price, sar, macd, macd_signal, rsi):
        return sar < price and macd > macd_signal and rsi < 30
    
    def checl_sell_signal(self, price, sar, macd, macd_signal, rsi):
        return sar > price and macd < macd_signal and rsi > 70

    def trading_strategy(self):
        prices = self.fetch_data()
        if not self.validate_data(prices):
            return
        
        sar = self.fetch_indicator('sar')
        macd_data = self.fetch_indicator('macd')
        rsi = self.calculate_rsi(prices)

        if macd_data is not None:
            macd, macd_signal = macd_data
            trade_amount = self.calculate_trade_amount() # Berechnet Handelsbetrag

            if self.check_buy_signal(prices[-1], sar, macd, macd_signal, rsi):
                self.execute_order('buy', trade_amount)
            elif self.checl_sell_signal(prices[-1], sar, macd, macd_signal, rsi):
                self.execute_order('sell', trade_amount)


# Hauptschleife
if __name__ == "__main__":
    api_key = 'YOUR_API_KEY'
    api_secret = 'YOUR_API_SECRET'
    bot = TradingBot(api_key, api_secret)

    while True:
        bot.trading_strategy()
        time.sleep(300)  # Wartezeit zwischen den Handelszyklen