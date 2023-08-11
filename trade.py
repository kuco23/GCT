import dotenv
from time import sleep
from lib import (
    ArticleProvider, TradeAdvisor, Exchange,
    logger, news_getters
)

config = dotenv.dotenv_values()

ACTION_INTERVAL = 60 * 30 # 30 minutes

openai_assistant_config = """
You are an experienced crypto trader. I will provide you with a list of recent crypto articles and
you will decide which cryptocurrencies to buy or sell. Your response is always in the form of either
"buy <asset> <time>" or "sell <asset>", where "asset" is the symbol of the relevant cryptocurrency,
and "time" is the number of hours to hold the bought cryptocurrency. If you want to sell
all cryptocurrencies respond with "sell all". I will then execute the trade for you.
"""
exchange_config = {
    'apiKey': config['EXCHANGE_API_KEY'],
    'secret': config['EXCHANGE_SECRET']
}

articleProvider = ArticleProvider(news_getters)
tradeAdvisor = TradeAdvisor(openai_assistant_config, config['GPT_MODEL_NAME'], config['OPENAI_SECRET'])
exchange = Exchange(config['EXCHANGE'], exchange_config)

while True:
    try:
        articles = articleProvider.getArticles()
        trade_advices = tradeAdvisor.getTradeAdvices(articles)
        exchange.executeNewTradeAdviceBatch(trade_advices)
    except Exception as e:
        logger.error(f'unhandled exception {e}')
    sleep(ACTION_INTERVAL)