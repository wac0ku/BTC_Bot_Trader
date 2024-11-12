import time
import logging
from binance.client import Client
from binance.enums import *

# Logging konfigurieren
logging.basicConfig(
    filename='trading_bot.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class BinanceTradingBot:
    def __init__(self, api_key, api_secret, symbol, minimum_balance):
        self.client = Client(api_key, api_secret)
        self.symbol = symbol
        self.minimum_balance = minimum_balance

    def get_balance(self):
        """Fetch the USDT balance."""
        balance_info = self.client.get_asset_balance(asset='USDT')
        return float(balance_info['free'])

    def get_current_price(self):
        """Fetch the current market price for the specified symbol."""
        avg_price = self.client.get_avg_price(symbol=self.symbol)
        return float(avg_price['price'])

    def place_buy_order(self, quantity):
        """Place a market order to buy the specified quantity."""
        order = self.client.order_market(
            symbol=self.symbol,
            side=SIDE_BUY,
            quantity=quantity
        )
        logging.info(f"Buy order placed: {order}")
        return order

    def place_sell_order(self, quantity):
        """Place a market order to sell the specified quantity."""
        order = self.client.order_market(
            symbol=self.symbol,
            side=SIDE_SELL,
            quantity=quantity
        )
        logging.info(f"Sell order placed: {order}")
        return order

    def execute_strategy(self):
        """Main trading strategy execution loop."""
        while True:
            current_price = self.get_current_price()
            balance = self.get_balance()
            max_investment = balance - self.minimum_balance

            if max_investment <= 0:
                logging.warning("Nicht genügend USDT verfügbar, um eine Order zu platzieren.")
                break

            quantity_to_buy = max_investment / current_price  # Berechne die Menge, die gekauft werden kann

            print(f"Current Price: {current_price}, Max Investable: {max_investment}, Quantity to Buy: {quantity_to_buy}")

            # Beispielbedingung für den Kauf
            if current_price * 1.02 <= current_price:  # Hier kannst du deine Kaufbedingung anpassen
                print(f"Placing buy order for {quantity_to_buy} BTC at {current_price}")
                self.place_buy_order(quantity_to_buy)
                break

            time.sleep(5)  # Warte vor der nächsten Überprüfung

if __name__ == "__main__":
    API_KEY = 'your_api_key'
    API_SECRET = 'your_api_secret'
    SYMBOL = 'BTCUSDT'
    MINIMUM_BALANCE = 100  # Mindestbalance in USDT, die nicht aufgebraucht werden soll

    bot = BinanceTradingBot(API_KEY, API_SECRET, SYMBOL, MINIMUM_BALANCE)
    bot.execute_strategy()