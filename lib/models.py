from typing import List
from collections import namedtuple
from datetime import datetime, timedelta
import re, json, openai, ccxt

TradeAdvice = namedtuple('TradeAdvice', ['position', 'asset', 'duration'])
TradeOrder = namedtuple('Order', ['position', 'asset', 'amount', 'duration'])

class ArticleProvider:

    def __init__(self, article_getters, logger):
        self._article_getters = article_getters
        start_time = datetime.now() - timedelta(minutes=90)
        self._last_updated = [start_time for _ in range(len(article_getters))]
        self._logger = logger

    def getArticles(self):
        articles = []
        for i, (last_updated, article_getter) in enumerate(zip(
            self._last_updated, self._article_getters
        )):
            for article, article_time in article_getter():
                if article_time > self._last_updated[i]:
                    articles.append(article)
                    if article_time > last_updated:
                        last_updated = article_time
                    self._logger.info('trading on article "%s"', article['title'])
            self._last_updated[i] = last_updated
        return articles

class TradeAdvisor:
    _parser_regex = re.compile('(?P<pos>buy|sell) (?P<symbol>[A-Z]{3,4})(?P<duration>[0-9]{1,2})?')

    def __init__(self, ai_assistant_config, api_key, logger):
        self.ai_assistant_config = ai_assistant_config
        self._logger = logger
        openai.api_key = api_key

    def _getGptResponse(self, prompt):
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
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
                symbol = 'AVAX'
            trade_advices.append(TradeAdvice(pos, symbol, int(duration or 0)))
        return trade_advices

    def getTradeAdvices(self, articles):
        gpt_response = self._getGptResponse(json.dumps(articles))
        self._logger.info(f'chat-gpt trade advice: {gpt_response}')
        trade_advices = self._parseGptResponse(gpt_response)
        self._logger.info(f'parsed trade advice: {trade_advices}')
        return trade_advices

class Exchange:

    def __init__(self, exchange_name, config, logger, max_fee=0.001):
        self.exchange = getattr(ccxt, exchange_name)(config)
        self.max_fee = max_fee

        self._logger = logger
        self._asset_balances = {}
        self._buy_time = {}
        self._sell_time = {}

        self._refreshBalances()
        self._sellAllAssets() # need implemented db

    def _convertUsdtToAssetWithPrice(self, usdt_amount, asset_price):
        return usdt_amount / asset_price

    def _convertUsdtToAsset(self, asset, usdt_amount):
        asset_price = self.exchange.fetch_ticker(f'{asset}/USDT')['last']
        return self._convertUsdtToAssetWithPrice(usdt_amount, asset_price)

    def _refreshBalances(self):
        self._asset_balances = {}
        exchange_balance = self.exchange.fetch_balance()['info']['balances']
        for info in exchange_balance:
            self._asset_balances[info['asset']] = float(info['free'])

    def _executeOrder(self, order: TradeOrder):
        if order.asset not in self._asset_balances: self._refreshBalances()
        if order.asset not in self._asset_balances: return
        symbol = f'{order.asset}/USDT'
        if order.position == 'buy':
            self.exchange.create_market_buy_order(symbol, format(order.amount, 'f'))
            self._buy_time[order.asset] = datetime.now()
            self._sell_time[order.asset] = datetime.now() + timedelta(hours=order.duration)
        elif order.position == 'sell':
            self.exchange.create_market_sell_order(symbol, format(order.amount, 'f'))
            del self._buy_time[order.asset]
            del self._sell_time[order.asset]
        else: return
        self._logger.info(f'executed {order}')

    def _sellAsset(self, asset, percent=100):
        try:
            amount_asset = self._asset_balances[asset] * percent / 100 * (1 - self.max_fee)
            if amount_asset > 0:
                self._executeOrder(TradeOrder('sell', asset, amount_asset, None))
        except Exception as e:
            self._logger.info(f'failed to sell {asset} because {e}')

    def _buyAsset(self, asset, percent=100, duration=24):
        amount_usdt = self._asset_balances['USDT'] * percent / 100 * (1 - self.max_fee)
        if amount_usdt == 0: self._logger.info(f'cannot buy {asset} because no USDT')
        try:
            amount_asset = self._convertUsdtToAsset(asset, amount_usdt)
            if amount_asset > 0:
                self._executeOrder(TradeOrder('buy', asset, amount_asset, duration))
        except Exception as e:
            self._logger.info(f'failed to buy {asset} because {e}')

    def _sellAllAssets(self):
        for asset, balance in self._asset_balances.items():
            if balance > 0 and asset != 'USDT':
                self._sellAsset(asset)

    def _sellOverdueAssets(self):
        for asset, time in self._sell_time.items():
            if datetime.now() > time:
                self._sellAsset(asset)

    def sellRequiredAssets(self):
        self._sellOverdueAssets()

    def executeTradeAdvice(self, advice: TradeAdvice):
        if advice.position == 'buy':
            self._buyAsset(advice.asset, 20, advice.duration)
        elif advice.position == 'sell':
            if advice.asset == 'all': self._sellAllAssets()
            if advice.asset in self._asset_balances:
                self._sellAsset(advice.asset)