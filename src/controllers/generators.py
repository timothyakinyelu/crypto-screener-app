from flask import json, current_app
from binance.client import Client
from datetime import datetime, timedelta
from src.controllers.indicators import run_indicators
from src import cache
from pathlib import Path
import requests
import pandas as pd
import os
import zc.lockfile


client = Client(os.environ.get('BINANCE_API_KEY'), os.environ.get('BINANCE_SECRET_KEY'), {"timeout": 100})
    
def generate_candlesticks(symbol):
    """ Generate candlestick files for each crypto"""
    
    try:
        dataLock = Path('src/datasets/lock/')
        lockfile = dataLock / '{}_lock'.format(symbol)
        lock = zc.lockfile.LockFile(lockfile)
        
        # if lockfile:
        #     pass
        # else:
        start_date = datetime.now() - timedelta(days=24)
        end_date = datetime.now()
        
        startValue = int(datetime.timestamp(start_date)  * 1000)
        endValue = int(datetime.timestamp(end_date) * 1000)
        
        dataFolder = Path('src/datasets/cryptodata/')
        dataFile = dataFolder / '{}_candles.csv'.format(symbol)
        dataFile2 = dataFolder / '{}_result.json'.format(symbol)
        
        filename = dataFile
        indicatorsFile = dataFile2
        
        try:
            if os.path.exists(filename):
                df = pd.read_csv(filename, header=None)
                # get last timestamp from dataframe
                last_timestamp = int(df.tail(1).iloc[0].get(0)) + (30 * 60 * 1000)
                
                candles = client.get_klines(
                    symbol = symbol,
                    interval = Client.KLINE_INTERVAL_30MINUTE,
                    startTime = last_timestamp,
                    endTime = endValue
                )
                
                # remove rows from top based on length of new candles fetched
                index_to_delete = len(candles)
                df = df.iloc[index_to_delete:]
                
                # remove columns that aren't needed from the candles
                for line in candles:
                    del line[6:]
                    
                df2 = pd.DataFrame(candles)
                df3 = df.append(df2)
                
                # write new dataframe to csv with updated rows
                with open(filename, 'w') as f:
                    df3.to_csv(f, header=None, index=False)   
            else:
                candles = client.get_klines(
                    symbol = symbol,
                    interval = Client.KLINE_INTERVAL_30MINUTE,
                    startTime = startValue,
                    endTime = endValue
                )
                
                # remove columns that aren't needed from the candles
                if candles:
                    for line in candles:
                        del line[6:]
                        
                    df = pd.DataFrame(candles)
                    df.to_csv(filename, header=None, index=False)
                else:
                    pass
            result = run_indicators(symbol, filename)
            with open(indicatorsFile, 'w') as f:
                json.dump(result, f)
                
            cache.set('{}_file'.format(symbol), indicatorsFile)
            lock.close()
        except requests.exceptions.ReadTimeout:
            pass
    except zc.lockfile.LockError:
        pass