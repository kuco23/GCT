# gpt-crypto-trading
This is a small project that connects a crypto news api, chatGPT, and a trading api to create a trading bot that trades crypto based on news.
The app will buy/sell assets determined by chatGPT based on the recent news, where buy positions will be held for a time also determined by chatGPT.

By default the app uses [cryptonews-api](https://cryptonews-api.com/) for news and binance as a trading platform.

## Setup and running
To configure the repo, you should fill in the `template.env` file with api keys, then rename it to `.env`.
Running the trading bot then requires running
```python
python trade.py
```
The app will first convert all your assets to USDT. Any time a buy order is required, it spends 50% of user USDT balance.
The app runs indefinitely, but can break due to many unhandled errors. To stop it, press `ctrl + c`.
> **Note:**
> Use at your own risk. This is a simple non-professional project.

## Changing defaults
To change or add crypto news sources, you can edit the `lib/cryptonews.py` file. All sources need to return a list of tuples of the form `(news, timestamp)`, where `news` is any data and `timestamp` is the time at which the news was published.

The trading platform can be changed from binance to any supported by the [ccxt](https://github.com/ccxt/ccxt) library, though note that other platforms have not been tested.

## TODO
- [ ] Handle connection errors when fetching news, querying chatGPT, and making trades.
- [ ] Make a database logging when timed-bought assets are supposed to get sold.
- [ ] Test with platforms different from binance.