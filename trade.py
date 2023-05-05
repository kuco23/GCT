from dotenv import dotenv_values
import logging
from time import sleep
from lib import ArticleProvider, TradeAdvisor, Exchange, getFileLogger

config = dotenv_values()

INFORMED_SELL_INTERVAL = 60 * 10 # 10 minutes
EVENT_FETCH_INTERVAL = 60 * 30 # 30 minutes

cryptonews_url_events = f'https://cryptonews-api.com/api/v1/events?&items=10&token={config["CRYPTONEWS_API_KEY"]}'
cryptonews_url_news = f'https://cryptonews-api.com/api/v1/category?section=alltickers&items=10&page=1&token={config["CRYPTONEWS_API_KEY"]}'
openai_assistant_config = """
You are an experienced crypto trader. I will provide you with a list of recent crypto articles and
you will decide which cryptocurrencies to buy or sell. Your response is always in one of two formats:
"buy <asset> <time>" or "sell <asset>", where "asset" is the symbol of the relevant cryptocurrency,
and "time" is the number of hours for which to hold the bought cryptocurrency. If you want to sell
all cryptocurrencies respond with "sell all". Please make your responses follow the described format.
I will then execute the trade for you.
"""
exchange_config = {
    'apiKey': config['EXCHANGE_API_KEY'],
    'secret': config['EXCHANGE_SECRET']
}

logger = getFileLogger('trade')
articleProvider = ArticleProvider(cryptonews_url_events, logger)
tradeAdvisor = TradeAdvisor(openai_assistant_config, config['OPENAI_SECRET'], logger)
exchange = Exchange(config['EXCHANGE'], exchange_config, logger)

slept = 0
while True:
    if slept > EVENT_FETCH_INTERVAL:
        slept = 0
        articles = articleProvider.getArticles()
        if len(articles) > 0:
            tradeAdvice = tradeAdvisor.getTradeAdvice(articles)
            if tradeAdvice is not None:
                exchange.executeTradeAdvice(tradeAdvice)
        else:
            logger.info('no new articles')
    exchange.sellRequiredAssets()
    sleep(INFORMED_SELL_INTERVAL)
    slept += INFORMED_SELL_INTERVAL