from typing import List, Callable, Literal as LiteralString
from time import sleep
from datetime import datetime, timedelta
import re, json, openai, ccxt
from requests.exceptions import ConnectionError, ReadTimeout

from ._storage import getPositions, storePositions
from ._shared import logger, TradeAdvice, TradeOrder, ArticleData


CONNECTION_RETRY_PERIOD = 2 # seconds
CONNECTION_RETRY_COUNT = 3 # times to retry connection
MINUMUM_BUY_AMOUNT = 10 # USDT

def forceResponse(fun):
    def wrapper(self, *args):
        outside_scope_err = None # ok have no idea why err is not in scope
        for _ in range(CONNECTION_RETRY_COUNT):
            try: return fun(self, *args)
            except ConnectionError as err:
                outside_scope_err = err
                logger.error('handled exception', err)
            except ReadTimeout as err:
                outside_scope_err = err
                logger.error('handled exception', err)
            except Exception as err:
                outside_scope_err = err
                logger.error('handled exception', err)
                break
            sleep(CONNECTION_RETRY_PERIOD)
        if fun.__name__ == '_sellAsset':
            logger.error(f'failed selling {args[0]} because {outside_scope_err}')
        elif fun.__name__ == '_buyAsset':
            logger.error(f'failed buying {args[0]} because {outside_scope_err}')
    return wrapper

class ArticleProvider:

    def __init__(self, article_getters: List[Callable[[], List[ArticleData]]]):
        self._article_getters = article_getters
        start_time = datetime(1970, 1, 1)
        self._last_updated = [start_time for _ in range(len(article_getters))]

    def getArticles(self) -> List[ArticleData]:
        articles = []
        for i, (last_updated, article_getter) in enumerate(zip(
            self._last_updated, self._article_getters
        )):
            for article, article_time in article_getter():
                if article_time > self._last_updated[i]:
                    articles.append(article)
                    if article_time > last_updated:
                        last_updated = article_time
                    logger.info('trading on article "%s"', article.get('title'))
            self._last_updated[i] = last_updated
        return articles

class TradeAdvisor:
    _parser_regex = re.compile('(?P<pos>buy|Buy|sell|Sell) (?P<symbol>[A-Z]{3,4}|all)(?: (?P<duration>[0-9]{1,2}))?')

    def __init__(self, ai_assistant_config: LiteralString, ai_model_name: LiteralString, api_key: LiteralString):
        self.ai_assistant_config = ai_assistant_config
        self.ai_model_name = ai_model_name
        openai.api_key = api_key

    def getTradeAdvices(self, articles: List[ArticleData]) -> List[TradeAdvice]:
        if len(articles) > 0:
            gpt_response = self._getGptResponse(json.dumps(articles))
            logger.info(f'chat-gpt trade advice:\n{gpt_response}')
            trade_advices = self._parseGptResponse(gpt_response)
            logger.info(f'parsed trade advice: {trade_advices}')
            return trade_advices
        else: return []

    def _getGptResponse(self, prompt):
        completion = openai.ChatCompletion.create(
            model=self.ai_model_name,
            messages=[
                {"role": "system", "content": self.ai_assistant_config},
                {"role": "user", "content": prompt}
            ]
        )
        return completion.choices[0].message.content

    def _parseGptResponse(self, response) -> List[TradeAdvice]:
        parsed_raw = self._parser_regex.findall(response)
        trade_advices = []
        for pos, symbol, duration in parsed_raw:
            if pos == 'buy' and symbol == 'all':
                symbol = 'BTC'
            trade_advices.append(TradeAdvice(pos.lower(), symbol, int(duration or 24)))
        return trade_advices

class Exchange:

    def __init__(self, exchange_name: LiteralString, config, max_fee=0.001):
        self.exchange = getattr(ccxt, exchange_name)(config)
        self.max_fee = max_fee
        self._cached_balances = {}
        self._cached_positions = {}

    def executeNewTradeAdviceBatch(self, advices: List[TradeAdvice]):
        self._cacheBalances()
        self._cachePositions()
        self._sellOverdueAssets()
        for advice in sorted(advices, key=lambda x: (x.position == 'buy', x.duration)):
            self._executeTradeAdvice(advice)
        storePositions(self._cached_positions)

    def _executeTradeAdvice(self, advice: TradeAdvice):
        if advice.asset == 'USDT': return
        if advice.position == 'buy':
            self._buyAsset(advice.asset, 50, advice.duration)
        elif advice.position == 'sell':
            if advice.asset == 'all':
                # self._sellAllAssets()
                pass
            if advice.asset in self._cached_balances: # and advice.asset not in self._cached_positions:
                self._sellAsset(advice.asset)

    def _sellOverdueAssets(self):
        for asset in list(self._cached_positions.keys()): # dict can change length during iteration
            end_time = self._cached_positions[asset]['sell_time']
            if datetime.now() > end_time:
                self._sellAsset(asset)

    def _sellAllAssets(self):
        for asset, balance in list(self._cached_balances.items()):
            if balance > 0 and asset != 'USDT':
                self._sellAsset(asset)

    @forceResponse
    def _sellAsset(self, asset, percent=100):
        amount_asset = self._cached_balances[asset] * percent / 100 * (1 - self.max_fee)
        if amount_asset > 0:
            amount_usdt = self._assetToUSDT(asset, amount_asset)
            self._executeOrder(TradeOrder('sell', asset, amount_asset, None))
            self._cached_balances['USDT'] += amount_usdt

    @forceResponse
    def _buyAsset(self, asset, percent=100, duration=24):
        amount_usdt = self._cached_balances['USDT'] * percent / 100 * (1 - self.max_fee)
        if amount_usdt < MINUMUM_BUY_AMOUNT:
            logger.info(f'trying to buy {asset} with too little USDT')
        else:
            amount_asset = self._USDTToAsset(asset, amount_usdt)
            self._executeOrder(TradeOrder('buy', asset, amount_asset, duration))
            self._cached_balances['USDT'] -= amount_usdt

    def _executeOrder(self, order: TradeOrder):
        if order.asset not in self._cached_balances: return
        symbol = f'{order.asset}/USDT'
        if order.position == 'buy':
            self.exchange.create_market_buy_order(symbol, format(order.amount, 'f'))
            self._cached_positions[order.asset] = {
                'buy_time': datetime.now(),
                'sell_time': datetime.now() + timedelta(hours=order.duration)
            }
        elif order.position == 'sell':
            self.exchange.create_market_sell_order(symbol, format(order.amount, 'f'))
            if order.asset in self._cached_positions:
                del self._cached_positions[order.asset]
        else: return
        logger.info(f'executed {order}')

    def _assetToUSDT(self, asset, asset_amount):
        asset_price = self.exchange.fetch_ticker(f'{asset}/USDT')['last']
        return asset_amount * asset_price

    def _USDTToAsset(self, asset, usdt_amount):
        asset_price = self.exchange.fetch_ticker(f'{asset}/USDT')['last']
        return usdt_amount / asset_price

    def _cacheBalances(self):
        self._cached_balances = {}
        exchange_balance = self.exchange.fetch_balance()['info']['balances']
        for info in exchange_balance:
            self._cached_balances[info['asset']] = float(info['free'])

    def _cachePositions(self):
        self._cached_positions = getPositions()
