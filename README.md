# gpt-crypto-trading

This is a simple project that connecst [Crypto News API](https://cryptonews-api.com/), [ChatGPT](https://openai.com/blog/chatgpt) and [Binance](https://www.binance.com/en) to create a trading bot that trades crypto based on recent news, with strategies determined by chatGPT.

## How it works

Every 120 minutes the app fetches recent crypto news and feeds them to chatGPT to generate a trading strategy. The strategy consists of a tuple `(asset, buy/sell, duration)` where `duration` specifies for what time the bought asset should be held and defaults to 24h. Selling is done automatically after that duration. Note that every buy position spends 50% of the USDT balance.

> Formally, the selling of asset means to exchange it for USDT.

The app logs your positions in the `positions.json` and keeps a log in `trade.log` file. To change the interval between news fetching, change the `ACTION_INTERVAL` variable in `trade.py`.

## How to set up and run

First clone this repo and install dependencies specified in `pyproject.toml`. Then fill in `template.env` with your api keys and rename it to `.env`. Finally, run the app with

```python
python trade.py
```

The app runs indefinitely. To stop it, press `ctrl + c`.

> **Note:**
> This is a simple non-professional project, use at your own risk. There are no guarantees that it will work as intended and can break due to unhandled exceptions.

## Replacing crypto news source api

I am not promoting the cryptonews-api here in any way, and the code is generic enough to allow for any other news source. To do that you can edit the `lib/cryptonews.py` file and export the `news_getters` variable that stores a list of news getter functions. You do need to respect the specified type signature of the getter functions.

## Replacing trading platform

The trading platform can be changed from binance to any supported by the [ccxt](https://github.com/ccxt/ccxt) library, though note that other platforms have not been tested and may not work.

## TODO
- [x] Handle connection errors when fetching news, querying chatGPT, and making trades.
- [x] Make a database logging when timed-bought assets are supposed to get sold.
- [ ] Test with platforms different from binance,
- [ ] Do app as a CronJob.