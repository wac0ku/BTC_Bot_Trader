# Autor: Leon Gajtner
# Datum: 2024-11-13
# Trading Bot : Trading Bot for Binance

import logging
import time
import numpy as np

import ccxt

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
    def __init__(self, api_key, api_secret, symbol='BTC/USDT', risk_percentage=0.05):
        self.binance = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True
        })
        self.symbol = symbol
        self.risk_percentage = risk_percentage
        self.last_sar_signal = None # None, 'buy' or 'sell'
        self.previous_macd = None # Speichert vorherigen MACD-Wert

        rsi_window = 5

        # RSI Parameter
        self.rsi_buy_lower_bound = 30 - rsi_window 
        self.rsi_buy_upper_bound = 70 + rsi_window
        self.rsi_sell_lower_bound = 70 - rsi_window
        self.rsi_sell_upper_bound = 30 + rsi_window
    
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
        """
        Berechnet den Trade Betrag basierend auf der Risikostufe.

        :return amount: Trade Betrag in USDT
        """
        balance = self.fetch_balance()
        amount = balance * self.risk_percentage
        logger.info(f"Calculated trade amount: {amount} USDT based on balance: {balance} USDT")
        return amount

    def fetch_data(self, timeframe='5m', limit=500):
        """
        Erhält die aktuellsten Kursdaten.

        :param timeframe: Zeitraum der Daten (z.B. 5m, 15m, 1h)
        :param limit: Anzahl der Datenpunkte
        """
        try:
            ohlcv = self.binance.fetch_ohlcv(self.symbol, timeframe=timeframe, limit=limit)
            close_prices = [x[4] for x in ohlcv]
            logger.info(f'Fetched data for {self.symbol} with timeframe {timeframe} and limit {limit}')
            return np.array(close_prices)
        except Exception as e:
            logger.error(f'Failed to fetch data for {self.symbol}: {str(e)}')
            return None

    def validate_data(self, prices):
        """
        Validiert die Daten.
        
        :param prices: Geschlossener Preis
        :return: True wenn Daten gültig sind, False sonst
        """
        if prices is None or len(prices) == 0:
            logger.error('No prices available for validation.')
            return False
        if np.any(np.isnan(prices)):
            logger.error('Prices contain NaN values.')
            return False
        return True

    def fetch_indicator(self, indicator):
        """
        Erhält die Daten für die Indikatoren.

        :param indicator: Indikator
        :return: Daten für den Indikator
        """
        try:
            params = {}
            if indicator == 'macd':
                params = {
                    "fast_length": 6,
                    "slow_length": 16,
                    "signal_length": 9
                }
            # fühe die Abfrage des Indikators durch
            data = self.binance.fetch_ta_indicator(self.symbol, params=params)
            logger.info(f"Fetched {indicator} data for {self.symbol}")
            return data['value'][-1]
        except Exception as e:
            logger.error(f"Failed to fetch {indicator} data for {self.symbol}: {str(e)}")
            return None

    def calculate_sar(self, prices, acceleration=0.02, maximum=0.2):
        """
        Berechnet den Parabolic SAR basierend auf den geschlossenen Preisen.

        :param prices: geschlossene Preise
        :param acceleration: Beschleunigungsfaktor
        :param maximum: maximaler Beschleunigungsfaktor
        :return: Liste der SAR-Werte
        """
        sar = [prices[0]]  # Initialisiere den ersten SAR-Wert
        ep = prices[0]  # Extrempreis
        trend = 1  # 1 für Aufwärtstrend, -1 für Abwärtstrend

        for i in range(1, len(prices)):
            sar.append(sar[i - 1] + acceleration * (ep - sar[i - 1]))

        if trend == 1:  # Aufwärtstrend
            if prices[i] < sar[i]:  # Trendwechsel
                trend = -1
                sar[i] = ep  # Setze SAR auf den Extrempreis
                ep = prices[i]  # Setze Extrempreis auf den aktuellen Preis
                acceleration = 0.02  # Zurücksetzen des Beschleunigungsfaktors
            else:
                if prices[i] > ep:
                    ep = prices[i]  # Aktualisiere Extrempreis
                    acceleration = min(acceleration + 0.02, maximum)  # Erhöhe den Beschleunigungsfaktor
        else:  # Abwärtstrend
            if prices[i] > sar[i]:  # Trendwechsel
                trend = 1
                sar[i] = ep  # Setze SAR auf den Extrempreis
                ep = prices[i]  # Setze Extrempreis auf den aktuellen Preis
                acceleration = 0.02  # Zurücksetzen des Beschleunigungsfaktors
            else:
                if prices[i] < ep:
                    ep = prices[i]  # Aktualisiere Extrempreis
                    acceleration = min(acceleration + 0.02, maximum)  # Erhöhe den Beschleunigungsfaktor
        
        return sar

    def calculate_rsi(self, prices, period=6):
        """
        Berechnet den Relative Strength Index (RSI) basierend auf den geschlossenen Preisen.

        :param prices: geschlossene Preise
        :param period: Zeitraum für die RSI Berechnung
        :return rsi: RSI Wert
        """
        if len(prices) < period:
            logger.error('Not enough prices available for RSI calculation.')
            return None

        delta = np.diff(prices[-period:])
        gain = (delta[delta > 0]).mean() if np.any(delta > 0) else 0
        loss = (-delta[delta < 0]).mean() if np.any(delta < 0) else 0
        rs = gain / loss if loss != 0 else 0
        rsi = 100 - (100 / (1 + rs))
        logger.info(f'Calculated RSI: {rsi} for period: {period}')
        return rsi

    def execute_order(self, order_type, amount):
        """
        Führt den Kauf oder Verkauf aus.

        :param order_type: 'buy' oder 'sell'
        :param amount: Anzahl der Coins
        :return order: Bestätigung der Order
        """
        try:
            if order_type == 'buy':
                order = self.binance.place_market_buy_order(self.symbol, amount)
                return order
            elif order_type == 'sell':
                order = self.binance.place_market_sell_order(self.symbol, amount)
                logger.info(f'Executed {order_type} order: {order}')
                return order
        except Exception as e:
            logger.error(f"Failed to execute {order_type} order: {str(e)}")
            return None
    
    def check_buy_signal(self, price, sar, macd_crossover, rsi):
        """
        Kaufsignal basierend auf den Indikatoren.

        :param price: aktuelle Kurs
        :param sar: SAR-Wert
        :param macd: MACD-Wert
        :param macd_signal: MACD-Signal-Wert
        :param rsi: RSI-Wert
        :return: True, wenn Kaufsignal
        """
        return sar < price and macd_crossover == 'bullish' and rsi <= self.rsi_buy_upper_bound and rsi >= self.rsi_buy_lower_bound

    def check_sell_signal(self, price, sar, macd_crossover, rsi):
        """
        Verkaufsignal basierend auf den Indikatoren.
        
        :param price: aktuelle Kurs
        :param sar: SAR-Wert
        :param macd: MACD-Wert
        :param macd_signal: MACD-Signal-Wert
        :param rsi: RSI-Wert
        :return: True, wenn Verkaufsignal
        """
        return sar > price and macd_crossover == 'baerish' and rsi >= self.rsi_sell_lower_bound and rsi <= self.rsi_sell_upper_bound

    def trading_strategy(self):
        """
        Die Tradingstrategie, die auf den Indikatoren basiert.
        """
        prices = self.fetch_data()
        if not self.validate_data(prices):
            return
        
        sar = self.calculate_sar(prices)
        macd_data = self.fetch_indicator('macd')
        rsi = self.calculate_rsi(prices)

        if macd_data is not None:
            macd, macd_signal = macd_data

            if self.previous_macd is not None:
                macd_crossover = None
                if self.previous_macd < macd and macd_signal < macd: # Bullish Crossover
                    macd_crossover = 'bullish'
                elif self.previous_macd > macd and macd_signal > macd: # Bearish Crossover
                    macd_crossover = 'bearish'
            
            trade_amount = self.calculate_trade_amount() # Berechnet Handelsbetrag
            
            # Kaufsignal
            if self.check_buy_signal(prices[-1], sar, macd_crossover, rsi):
                if self.last_sar_signal != 'buy':
                    self.last_sar_signal = 'buy'
                    self.execute_order('buy', trade_amount)
            
            # Verkaufsignal
            elif self.check_sell_signal(prices[-1], sar, macd_crossover, rsi):
                if self.last_sar_signal != 'sell':
                    self.last_sar_signal = 'sell'
                    self.execute_order('sell', trade_amount)

# Hauptschleife
if __name__ == "__main__":
    api_key = 'YOUR_API_KEY'
    api_secret = 'YOUR_API_SECRET'
    bot = TradingBot(api_key, api_secret)

    while True:
        bot.trading_strategy()
        time.sleep(300)  # Wartezeit zwischen den Handelszyklen