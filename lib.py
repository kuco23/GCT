from collections import namedtuple
from datetime import datetime, timedelta
import logging, json, requests, openai, ccxt

TradeAdvice = namedtuple('TradeAdvice', ['position', 'asset', 'duration'])
TradeOrder = namedtuple('Order', ['position', 'asset', 'amount', 'duration'])

class ArticleProvider:

    def __init__(self, source_url, logger):
        self.source_url = source_url
        self._last_article_time = datetime(1970, 1, 1)
        self._logger = logger

    # should override if source is not cryptonews
    def _formatDate(self, date):
        date = ' '.join(date.split(',')[1].strip().split()[:-1])
        return datetime.strptime(date, '%d %b %Y %H:%M:%S')

    # should override if source is not cryptonews
    def _getRawArticles(self):
        return json.loads(requests.get(self.source_url).content)['data']

    def getArticles(self):
        articles = []
        last_article_time = self._last_article_time
        for article in self._getRawArticles():
            article_time = self._formatDate(article['date'])
            if article_time > self._last_article_time:
                articles.append({
                    'title': article['event_name'],
                    'text': article['event_text']
                })
                if article_time > last_article_time:
                    last_article_time = article_time
                self._logger.info('trading on event "%s"', article['event_name'])
        self._last_article_time = last_article_time
        return articles

class TradeAdvisor:

    def __init__(self, ai_assistant_config, api_key, logger):
        self.ai_assistant_config = ai_assistant_config
        openai.api_key = api_key
        self._logger = logger

    def _getGptResponse(self, prompt):
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": self.ai_assistant_config},
                {"role": "user", "content": prompt}
            ]
        )
        return completion.choices[0].message.content

    def _parseGptResponse(self, response) -> TradeAdvice:
        parts = response.split()
        if len(parts) <= 1: return
        position, asset, *parts = parts
        if position == 'sell':
            return TradeAdvice(position, asset, None)
        elif position == 'buy':
            if len(parts) == 2: return
            if asset == 'all': asset = 'BTC'
            duration = parts[0]
            if not duration.isdigit(): return
            return TradeAdvice(position, asset, int(duration))

    def getTradeAdvice(self, articles):
        response = self._getGptResponse(json.dumps(articles))
        parsed = self._parseGptResponse(response)
        if parsed is not None:
            self._logger.info('trade advice: %s', parsed)
            return self._parseGptResponse(response)
        self._logger.info('invalid gpt response: %s', response)

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

    def _convertPricedAssetToUSDT(self, usdt_amount, asset_price):
        return usdt_amount / asset_price

    def _convertAssetToUSDT(self, asset, usdt_amount):
        asset_price = self.exchange.fetch_ticker(f'{asset}/USDT')['last']
        return self._convertPricedAssetToUSDT(usdt_amount, asset_price)

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
            self.exchange.create_market_buy_order(symbol, order.amount)
            self._buy_time[order.asset] = datetime.now()
            self._sell_time[order.asset] = datetime.now() + timedelta(hours=order.duration)
        elif order.position == 'sell':
            self.exchange.create_market_sell_order(symbol, order.amount)
            del self._buy_time[order.asset]
            del self._sell_time[order.asset]
        else: return
        self._logger.info(f'executed {order}')

    def _sellAsset(self, asset, percent=100):
        return
        amount_asset = self._asset_balances[asset] * percent / 100 * (1 - self.max_fee)
        if amount_asset > 0:
            try:
                self._executeOrder(TradeOrder('sell', asset, amount_asset, None))
            except Exception as e:
                self._logger.info(f'failed to sell {asset} because {e}')

    def _buyAsset(self, asset, percent=100, duration=24):
        amount_usdt = self._asset_balances['USDT'] * percent / 100 * (1 - self.max_fee)
        amount_asset = self._convertAssetToUSDT(asset, amount_usdt)
        if amount_asset > 0:
            try:
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
                self._executeOrder(TradeOrder('sell', asset, self._asset_balances[asset]))

    def sellRequiredAssets(self):
        self._sellOverdueAssets()

    def executeTradeAdvice(self, advice: TradeAdvice):
        if advice.position == 'buy':
            self._buyAsset(advice.asset, 20, advice.duration)
        elif advice.position == 'sell':
            if advice.asset == 'all': self._sellAllAssets()
            if advice.asset in self._asset_balances:
                self._sellAsset(advice.asset)

def getConsoleLogger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger

def getFileLogger(name):
    # create logger with 'spam_application'
    logger = logging.getLogger('spam_application')
    logger.setLevel(logging.DEBUG)
    # create file handler which logs even debug messages
    fh = logging.FileHandler('spam.log')
    fh.setLevel(logging.DEBUG)
    logger.addHandler(fh)
    return logger