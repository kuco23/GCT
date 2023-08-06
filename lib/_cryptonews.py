from typing import List, Callable
from datetime import datetime
import json, requests
from ._shared import config, ArticleData


cryptonews_url_events = f'https://cryptonews-api.com/api/v1/events?&items=10&token={config["CRYPTONEWS_API_KEY"]}'
cryptonews_url_news = f'https://cryptonews-api.com/api/v1/category?section=alltickers&items=10&page=1&token={config["CRYPTONEWS_API_KEY"]}'

# should override if source is not cryptonews
def _formatDate(date):
    date = ' '.join(date.split(',')[1].strip().split()[:-1])
    return datetime.strptime(date, '%d %b %Y %H:%M:%S')

# should override if source is not cryptonews
def _getRawArticlesFromSource(source_url):
    return json.loads(requests.get(source_url).content)['data']

def news_getter() -> List[ArticleData]:
    articles = _getRawArticlesFromSource(cryptonews_url_news)
    return [({
        'title': article['title'],
        'text': article['text'],
        'symbols': article['tickers']
    }, _formatDate(article['date'])) for article in articles]

def events_getter() -> List[ArticleData]:
    articles = _getRawArticlesFromSource(cryptonews_url_events)
    return [({
        'title': article['event_name'],
        'text': article['event_text'],
        'symbols': article['tickers']
    }, _formatDate(article['date'])) for article in articles]

news_getters: List[Callable[[], List[ArticleData]]] = [news_getter, events_getter]