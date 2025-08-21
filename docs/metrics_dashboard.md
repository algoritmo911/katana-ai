# Metrics Dashboard: Katana AI Trading Bot

This document defines the key metrics for evaluating the performance of the trading bot prototype.

## Core Metrics

| Metric                | Description                                                                 | How to Track                                                              |
| --------------------- | --------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| `trades_executed`     | The total number of trades (buys or sells) executed successfully.           | Increment a counter every time a trade is confirmed and executed.         |
| `profit/loss`         | The net profit or loss from all trading activities.                         | Calculated based on the buy and sell prices of assets.                    |
| `user_confirm_rate`   | The percentage of trade suggestions that are confirmed by the user.         | (Number of Confirmed Trades / Number of Suggested Trades) * 100           |
| `suggestion_frequency`| How often the bot suggests a trade.                                         | Count the number of suggestions per day/week.                             |

## Data Points to Log

For each trade suggestion, we should log:
- Timestamp
- Suggested action (`BUY`/`SELL`)
- The `why-trace` (reason for the suggestion)
- User response (`confirmed`/`declined`/`ignored`)
- Timestamp of user response

For each executed trade, we should log:
- Timestamp
- Action (`BUY`/`SELL`)
- Amount and currency
- Price
- Fees
- Resulting profit/loss (for sells)

This data will be crucial for analyzing the effectiveness of the trading strategies and the user's interaction with the bot.
