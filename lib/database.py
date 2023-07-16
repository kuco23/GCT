from datetime import datetime
from pathlib import Path
import json


positions_path = Path('positions.json')

def _initJsonIfNotExists():
    if not positions_path.exists():
        positions_path.touch()
        with open(positions_path, 'w') as positions_file:
            json.dump({}, positions_file)

def getPositions():
    _initJsonIfNotExists()
    with open(positions_path, 'r') as positions_file:
        unparsed = json.load(positions_file)
    return {
        asset: {
            'buy_time': datetime.strptime(unparsed[asset]['buy_time'], '%Y-%m-%d %H:%M:%S.%f'),
            'sell_time': datetime.strptime(unparsed[asset]['sell_time'], '%Y-%m-%d %H:%M:%S.%f')
        } for asset in unparsed
    }

def storePositions(positions):
    with open(positions_path, 'w') as positions_file:
        json.dump({
            asset: {
                'buy_time': str(positions[asset]['buy_time']),
                'sell_time': str(positions[asset]['sell_time'])
            } for asset in positions
        }, positions_file)