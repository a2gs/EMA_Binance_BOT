#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Andre Augusto Giannotti Scota
# andre.scota@gmail.com
# MIT license

import os
import ema2
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceWithdrawException, BinanceRequestException

try:
	client = Client(os.getenv('BINANCE_APIKEY', 'NOTDEF_APIKEY'), os.getenv('BINANCE_SEKKEY', 'NOTDEF_APIKEY'), {"verify": True, "timeout": 20})


	time_res = client.get_server_time()
	print(f"Binance time: {time_res}")

	print('-------------')
	time_res = client.get_order_book(symbol='BTCUSDT')
	print(time_res)

	print('-------------')

#	info = client.get_symbol_info('BNBBTC')
#	print(info)

except BinanceAPIException as e:
	logging.info(f'Binance API exception: {e.status_code} - {e.message}')

except BinanceRequestException as e:
	logging.info(f'Binance request exception: {e.status_code} - {e.message}')

except BinanceWithdrawException as e:
	logging.info(f'Binance withdraw exception: {e.status_code} - {e.message}')
