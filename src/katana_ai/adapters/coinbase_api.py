import os
from coinbase.wallet.client import Client

class CoinbaseAPI:
    def __init__(self, api_key=None, api_secret=None):
        """
        Initializes the Coinbase API client.
        API keys can be passed directly or sourced from environment variables.
        """
        self.api_key = api_key or os.getenv("COINBASE_API_KEY")
        self.api_secret = api_secret or os.getenv("COINBASE_API_SECRET")

        if not self.api_key or not self.api_secret:
            raise ValueError("Coinbase API key and secret must be provided either as arguments or environment variables.")

        self.client = Client(self.api_key, self.api_secret)

    def get_primary_account(self):
        """
        Retrieves the primary account.
        """
        try:
            accounts = self.client.get_accounts()
            primary_account = next((acc for acc in accounts.data if acc.primary), None)
            return primary_account
        except Exception as e:
            print(f"Error getting primary account: {e}")
            return None

    def get_balance(self):
        """
        Retrieves the balance of the primary account.
        """
        account = self.get_primary_account()
        if account:
            return account.balance
        return None

    def get_spot_price(self, currency_pair='BTC-USD'):
        """
        Retrieves the spot price for a given currency pair.
        """
        try:
            price = self.client.get_spot_price(currency_pair=currency_pair)
            return price
        except Exception as e:
            print(f"Error getting spot price for {currency_pair}: {e}")
            return None

    def get_transaction_history(self):
        """
        Retrieves the transaction history for the primary account.
        """
        account = self.get_primary_account()
        if account:
            return self.client.get_transactions(account.id)
        return None

    def create_buy_order(self, amount, currency, payment_method_id):
        """
        Creates a buy order.
        """
        account = self.get_primary_account()
        if account:
            try:
                buy = self.client.buy(account.id,
                                      amount=amount,
                                      currency=currency,
                                      payment_method=payment_method_id)
                return buy
            except Exception as e:
                print(f"Error creating buy order: {e}")
                return None
        return None

    def create_sell_order(self, amount, currency):
        """
        Creates a sell order.
        """
        account = self.get_primary_account()
        if account:
            try:
                sell = self.client.sell(account.id,
                                        amount=amount,
                                        currency=currency)
                return sell
            except Exception as e:
                print(f"Error creating sell order: {e}")
                return None
        return None

    def execute_trade(self, trade_details):
        """
        A generic method to execute a trade (buy or sell).
        'trade_details' is a dictionary containing trade info.
        Example: {'action': 'buy', 'amount': '10', 'currency': 'BTC', 'payment_method_id': '...'}
        """
        action = trade_details.get('action')
        amount = trade_details.get('amount')
        currency = trade_details.get('currency')

        if action == 'buy':
            payment_method_id = trade_details.get('payment_method_id')
            if not all([amount, currency, payment_method_id]):
                raise ValueError("Missing parameters for buy order.")
            return self.create_buy_order(amount, currency, payment_method_id)
        elif action == 'sell':
            if not all([amount, currency]):
                 raise ValueError("Missing parameters for sell order.")
            return self.create_sell_order(amount, currency)
        else:
            raise ValueError(f"Unsupported trade action: {action}")
