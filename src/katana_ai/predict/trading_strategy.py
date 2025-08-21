import pandas as pd

class TradingStrategy:
    def __init__(self, historical_data_source=None):
        """
        Initializes the trading strategy module.
        'historical_data_source' should be an object that can provide historical price data.
        For this prototype, it's optional.
        """
        self.historical_data_source = historical_data_source

    def get_historical_prices(self, currency_pair, period='1H'):
        """
        Retrieves historical price data.
        This is a placeholder. In a real scenario, this would fetch data from an exchange or a database.
        """
        # In a real implementation, this would call self.historical_data_source.
        # For now, we'll use sample data to simulate a 6% drop.
        data = {
            'price': [100, 94]  # Simulates a 6% drop
        }
        df = pd.DataFrame(data)
        return df

    def analyze_market_and_suggest_action(self, currency_pair='BTC-USD'):
        """
        Analyzes market data and suggests a trading action based on simple heuristics.
        """
        try:
            prices_df = self.get_historical_prices(currency_pair)

            if len(prices_df) < 2:
                return {'action': 'HOLD', 'why-trace': 'Not enough data to make a decision.'}

            latest_price = prices_df['price'].iloc[-1]
            previous_price = prices_df['price'].iloc[-2]

            price_change_pct = ((latest_price - previous_price) / previous_price) * 100

            # Heuristic rule: Buy if price drops more than 5%
            if price_change_pct < -5.0:
                return {
                    'action': 'BUY',
                    'why-trace': f'Price dropped by {price_change_pct:.2f}%. Buying opportunity.'
                }

            # Heuristic rule: Sell if price increases more than 5%
            elif price_change_pct > 5.0:
                return {
                    'action': 'SELL',
                    'why-trace': f'Price increased by {price_change_pct:.2f}%. Selling for profit.'
                }

            # Otherwise, hold
            else:
                return {
                    'action': 'HOLD',
                    'why-trace': f'Price change ({price_change_pct:.2f}%) is within the hold threshold.'
                }

        except Exception as e:
            print(f"Error during market analysis: {e}")
            return {'action': 'HOLD', 'why-trace': f'An error occurred during analysis: {e}'}
