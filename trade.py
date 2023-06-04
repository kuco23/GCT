import dotenv
from time import sleep
from lib import (
    ArticleProvider, TradeAdvisor, Exchange,
    getFileLogger, news_getters
)

config = dotenv.dotenv_values()

INFORMED_SELL_INTERVAL = 60 * 10 # 10 minutes
EVENT_FETCH_INTERVAL = 60 * 30 # 30 minutes

openai_assistant_config = """
You are an experienced crypto trader. I will provide you with a list of recent crypto articles and
you will decide which cryptocurrencies to buy or sell. Your response is always in the form of either
"buy <asset> <time>" or "sell <asset>", where "asset" is the symbol of the relevant cryptocurrency,
and "time" is the number of hours for which to hold the bought cryptocurrency. If you want to sell
all cryptocurrencies respond with "sell all". I will then execute the trade for you, though note
that each trade has fees, so you should only respond when you are confident of the price change.
"""
exchange_config = {
    'apiKey': config['EXCHANGE_API_KEY'],
    'secret': config['EXCHANGE_SECRET']
}

logger = getFileLogger('trade')
articleProvider = ArticleProvider(news_getters, logger)
tradeAdvisor = TradeAdvisor(openai_assistant_config, config['GPT_MODEL_NAME'], config['OPENAI_SECRET'], logger)
exchange = Exchange(config['EXCHANGE'], exchange_config, logger)

slept = 0
while True:
    if slept > EVENT_FETCH_INTERVAL or slept == 0:
        slept = 0
        articles = articleProvider.getArticles()
        if len(articles) > 0:
            for tradeAdvice in tradeAdvisor.getTradeAdvices(articles):
                exchange.executeTradeAdvice(tradeAdvice)
        else:
            logger.info('no new articles')
    exchange.sellRequiredAssets()
    sleep(INFORMED_SELL_INTERVAL)
    slept += INFORMED_SELL_INTERVAL