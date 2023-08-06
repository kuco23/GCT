from collections import namedtuple
from pathlib import Path
import logging, dotenv


config = dotenv.dotenv_values()

ArticleData = namedtuple('ArticleData', ['title', 'text', 'symbols'])
TradeAdvice = namedtuple('TradeAdvice', ['position', 'asset', 'duration'])
TradeOrder = namedtuple('TradeOrder', ['position', 'asset', 'amount', 'duration'])

# if logger exists delete the file
log_path = Path('trade.log')
if log_path.exists():
    log_path.unlink()

# create trade logger
logger = logging.getLogger('trade_logger')
logger.setLevel(logging.DEBUG)
# create file handler which logs even debug messages
fh = logging.FileHandler('trade.log')
fh.setLevel(logging.DEBUG)
fh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(fh)
