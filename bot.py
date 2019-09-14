#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Andre Augusto Giannotti Scota
# andre.scota@gmail.com
# MIT license

import os
import sys
import atexit
import time
import errno
import signal
import logging

from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceWithdrawException, BinanceRequestException

class botCfg:
	cfg = {}

	def get(self, param):
		return self.cfg.get(param, 'UNDEF')

	def set(self, param, value):
		self.cfg[param] = value

cfg = botCfg()
runningBot = True # Used to stop/start bot main loop (cmds from pipe file)

# ----------------------------------------------------------------------------------------

def sigHandler(signum, frame):
	sys.stderr.write(f'Singal {signum} received\n')
	sys.exit(0)

def removePidFile():
	global cfg

	os.remove(cfg.get('pid_file_path'))
	os.remove(cfg.get('cmd_pipe_file_path'))

def daemonize():
	pid_num = 0
	global cfg

	try:
		pid_num = os.fork()
		if pid_num > 0:
			sys.exit(0)

	except OSError as e:
		sys.stderr.write(f"Fork failed: {e.errno} - {e.strerror}\n")
		sys.exit(1)

	cfg.set('pid', os.getpid())

	os.chdir(cfg.get('work_path'))
	os.setsid()
	os.umask(0)

	atexit.register(removePidFile)

	f = open(cfg.get('pid_file_path'), 'w+')
	f.write(f"{cfg.get('pid')}\n{cfg.get('cmd_pipe_file_path')}\n{cfg.get('log_file')}\n{cfg.get('work_path')}\n{cfg.get('binance_pair')}\n")
	f.close()

# ----------------------------------------------------------------------------------------

class ema:
	__ema = 0.0
	__k = 0
	__seed = 0.0

	def __init__(self, ema, ema_initPopulation):	
		self.__k = 2 / (ema + 1)
		self.__ema = ema
		self.__seed = sum(ema_initPopulation) / ema
#		print('---')
#		print(f'EMA: {self.__ema} seed: {self.__seed} len: ')
#		print(len(ema_initPopulation))
#		print(ema_initPopulation)

	def getCurrent(self):
		return(self.__seed)

	def insertNewValue(self, new):
		ret = ((new - self.__seed) * self.__k) + self.__seed
		self.__seed = ret
		return(ret)

	def forecastValue(self, new):
		ret = ((new - self.__seed) * self.__k) + self.__seed
		return(ret)

def runBot():
	global cfg
	global runningBot

	nextSrvIdTime = 0

	pair = cfg.get('binance_pair')

	logging.info("--- Wallet status ---\n")

	try:
		client = Client(cfg.get('binance_apikey'), cfg.get('binance_sekkey'), {"verify": True, "timeout": 20})

	except BinanceAPIException as e:
		logging.info(f'Binance API exception: {e.status_code} - {e.message}')
		return 1

	except BinanceRequestException as e:
		logging.info(f'Binance request exception: {e.status_code} - {e.message}')
		return 2

	except BinanceWithdrawException as e:
		logging.info(f'Binance withdraw exception: {e.status_code} - {e.message}')
		return 3

	# Exchange status
	if client.get_system_status()['status'] != 0:
		print('Binance out of service')
		return 1

	# 1 Pair wallet
	pair1 = client.get_asset_balance(pair[:3])
	logging.info(f'Symbol 1 on wallet: ['
		+ pair[:3] + ']\tFree: [' + pair1['free'] + ']\tLocked: [' + pair1['locked'] + ']')

	# 2 Pair wallet
	pair2 = client.get_asset_balance(pair[3:])
	logging.info(f'Symbol 2 on wallet: ['
		+ pair[3:] + ']\tFree: [' + pair2['free'] + ']\tLocked: [' + pair2['locked'] + ']')

	# Open orders
	openOrders = client.get_open_orders(symbol=pair)
	for openOrder in openOrders:
		logging.info(f'Order id [' + str(openOrder['orderId']) + '] data:\n' 
			+ '\tPrice.......: [' + openOrder['price']          + ']\n'
			+ '\tQtd.........: [' + openOrder['origQty']        + ']\n'
			+ '\tQtd executed: [' + openOrder['executedQty']    + ']\n'
			+ '\tSide........: [' + openOrder['side']           + ']\n'
			+ '\tType........: [' + openOrder['type']           + ']\n'
			+ '\tStop price..: [' + openOrder['stopPrice']      + ']\n'
			+ '\tIs working..: [' + str(openOrder['isWorking']) + ']')

	del pair1
	del pair2
	del openOrder
	del openOrders

# ---------

	logging.info("\n--- Loading data ---")

	lastPrices = []

	slow_emaAux = cfg.get('slow_ema')
	fast_emaAux = cfg.get('fast_ema')

	# the last candle is running, so it will be descarded
	try:
		closedPrices = client.get_klines(symbol=pair, interval=cfg.get('time_sample'))[-slow_emaAux-1:-1]

	except BinanceAPIException as e:
	   logging.info('Binance API exception: {e.status_code} - {e.message}')
	   return 1

	except BinanceRequestException as e:
	   logging.info('Binance request exception: {e.status_code} - {e.message}')
	   return 2

	except BinanceWithdrawException as e:
	   logging.info('Binance withdraw exception: {e.status_code} - {e.message}')
	   return 3

	for i in range(0, slow_emaAux):
		lastPrices.append(float(closedPrices[i][4]))

	#print('return closedPrices:')
	#print(closedPrices)
	#print(len(closedPrices))
	#print('---')

	#print("Prices:")
	#print(lastPrices)
	#print("Prices len:")
	#print(len(lastPrices))

	logging.info(f'Last completed candle time: {nextSrvIdTime}')

	emaSlow = ema(slow_emaAux, lastPrices)
	emaFast = ema(fast_emaAux, lastPrices[len(lastPrices) - fast_emaAux:])

	nextSrvIdTime = closedPrices[-1:][0][0] + 1

	del lastPrices
	del closedPrices
	del slow_emaAux
	del fast_emaAux

	logging.info(f'Initial slow EMA {emaSlow.getCurrent()} | Initial fast EMA {emaFast.getCurrent()}')

# ---------

	logging.info("\n--- Stating ---")

	# Pair price
	try:
		getPrice = client.get_symbol_ticker(symbol=cfg.get('binance_pair'))

	except BinanceAPIException as e:
		logging.info(f'Binance API exception: {e.status_code} - {e.message}')
		return 1

	except BinanceRequestException as e:
		logging.info(f'Binance request exception: {e.status_code} - {e.message}')
		return 2

	except BinanceWithdrawException as e:
		logging.info(f'Binance withdraw exception: {e.status_code} - {e.message}')
		return 3

	logging.info(f'Symbol: [' + getPrice['symbol'] + '] Price: [' + getPrice['price'] + ']')

	botIteracSleepMin = 1.5

	runningBot = True

	while runningBot:

		try:
			clast = client.get_klines(symbol=pair, interval=cfg.get('time_sample'))[-1:][0]

		except BinanceAPIException as e:
			logging.info(f'Binance API exception: {e.status_code} - {e.message}')
			return 1

		except BinanceRequestException as e:
			logging.info(f'Binance request exception: {e.status_code} - {e.message}')
			return 2

		except BinanceWithdrawException as e:
			logging.info(f'Binance withdraw exception: {e.status_code} - {e.message}')
			return 3

		cLastTimeId = clast[0]
		cLastPrice  = float(clast[4])

		if cLastTimeId == nextSrvIdTime:

			# Just a forecast for the current (not closed) candle

			logging.info(f'Current value: [{cLastPrice}] | Current time Id: [{cLastTimeId}] | Slow EMA prediction: [{emaSlow.forecastValue(cLastPrice)}] | Fast EMA prediction: [{emaFast.forecastValue(cLastPrice)}]')
			
		else:

# TODO: getting wrong element price ... (if it is a new node, cLastPrice must be the previous)

			calculatedSlowEMA = emaSlow.insertNewValue(cLastPrice)
			calculatedFastEMA = emaFast.insertNewValue(cLastPrice)

			cLastTimeId = nextSrvIdTime + 1

			logging.info(f'Closed candle! Value: [{cLastPrice}] | Time Id: [{cLastTimeId}] | Slow EMA: [{calculatedSlowEMA}] | Fast EMA: [{calculatedFastEMA}]')

			if calculatedSlowEMA < calculatedFastEMA:
				logging.info('S<F BUY')
			elif calculatedSlowEMA > calculatedFastEMA:
				logging.info('S>F SELL')
			else:
				logging.info('S=F')

		logging.info(f'Sleeping {botIteracSleepMin} minutes...\n')
		time.sleep(botIteracSleepMin * 60)

	return 0

# ----------------------------------------------------------------------------------------

def main(argv):
	ret = 0

	global cfg

	cfg.set('binance_apikey', os.getenv('BINANCE_APIKEY', 'NOTDEF_APIKEY'))
	cfg.set('binance_sekkey', os.getenv('BINANCE_SEKKEY', 'NOTDEF_APIKEY'))

	cfg.set('work_path', argv[1])
	cfg.set('pid_file_path', f"{argv[2]}_pid.text")
	cfg.set('cmd_pipe_file_path', f"{argv[2]}_pipecmd")
	cfg.set('log_file', f"{argv[2]}_log.text")
	cfg.set('binance_pair', argv[3])
	cfg.set('fast_ema', int(argv[4]))
	cfg.set('slow_ema', int(argv[5]))

	klineAPIIntervals = {
		'1m'  : Client.KLINE_INTERVAL_1MINUTE,
		'3m'  : Client.KLINE_INTERVAL_3MINUTE,
		'5m'  : Client.KLINE_INTERVAL_5MINUTE,
		'15m' : Client.KLINE_INTERVAL_15MINUTE,
		'30m' : Client.KLINE_INTERVAL_30MINUTE,
		'1h'  : Client.KLINE_INTERVAL_1HOUR,
		'2h'  : Client.KLINE_INTERVAL_2HOUR,
		'4h'  : Client.KLINE_INTERVAL_4HOUR,
		'6h'  : Client.KLINE_INTERVAL_6HOUR,
		'8h'  : Client.KLINE_INTERVAL_8HOUR,
		'12h' : Client.KLINE_INTERVAL_12HOUR,
		'1d'  : Client.KLINE_INTERVAL_1DAY,
		'3d'  : Client.KLINE_INTERVAL_3DAY,
		'1w'  : Client.KLINE_INTERVAL_1WEEK,
		'1M'  : Client.KLINE_INTERVAL_1MONTH
	}

	try:
		cfg.set('time_sample', klineAPIIntervals[argv[6]])

	except KeyError as e:
		print(f'Error: time sample {argv[6]} not defined. Use one of: ')
		print(klineAPIIntervals.keys())
		sys.exit(1)

	del klineAPIIntervals

	daemonize()

	signal.signal(signal.SIGILL, sigHandler)
	signal.signal(signal.SIGTRAP, sigHandler)
	signal.signal(signal.SIGINT, sigHandler)
	signal.signal(signal.SIGHUP, sigHandler)
	signal.signal(signal.SIGTERM, sigHandler)
	signal.signal(signal.SIGSEGV, sigHandler)

#	try:
#		logFile = open(cfg.get('log_file'), 'a')
	logging.basicConfig(filename=cfg.get('log_file'), filemode='a', level=logging.NOTSET, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y%m%d%H%M%S')

#	except IOError:
#		sys.stderr.write(f"Creating log file failed: {e.errno} - {e.strerror}\n")
#		sys.exit(1)

	logging.info(f"\n================================================================\nConfiguration:")
	logging.info(f"\tPID = [{cfg.get('pid')}]")
	logging.info(f"\tPID file = [{cfg.get('pid_file_path')}]")
	logging.info(f"\tCMD pipe = [{cfg.get('cmd_pipe_file_path')}]")
	logging.info(f"\tWorking path = [{cfg.get('work_path')}]")
	logging.info(f"\tBinance pair = [{cfg.get('binance_pair')}]")
	logging.info(f"\tEMA Slow/Fast = [{cfg.get('slow.ema')} / {cfg.get('fast_ema')}]")
	logging.info(f"\tTime sample = [{cfg.get('time_sample')}]")
	logging.info(f"\tBinance API key = [{cfg.get('binance_apikey')}]\n")

	try:
		os.mkfifo(cfg.get('cmd_pipe_file_path'))

	except OSError as e: 
		logging.info(f"Erro creating cmd pipe file: {e.errno} - {e.strerror}")
		sys.exit(1)

#	try:
#		CMD_PIPE_FILE = open(CMD_PIPE_FILE_PATH, "r")

#	except IOError:
#		sys.stderr.write(f"Opeing cmd pipe file failed: {e.errno} - {e.strerror}\n")
# 		sys.exit(1)

#	ret = runBot(logFile, BINANCE_PAIR, binance_apiKey, binance_sekKey)
	ret = runBot()

	logging.info(f"BOT return: [{ret}]")

#	CMD_PIPE_FILE.close()
	logFile.close()

	sys.exit(ret)

if __name__ == '__main__':

	if len(sys.argv) != 7:
		print(f"Usage:\n\t{sys.argv[0]} <BOT_ID> <WORK_PATH> <BINANCE_PAIR> <FAST_EMA> <SLOW_EMA> <TIME_SAMPLE>\nSample:\n\t{sys.argv[0]} ./ BOT1 BNBBTC\n")
		print("Where <TIME_SAMPLE>:"
			+ "\t1m = 1MINUTE\n"
			+ "\t3m = 3MINUTE\n"
			+ "\t5m = 5MINUTE\n"
			+ "\t15m = 15MINUTE\n"
			+ "\t30m = 30MINUTE\n"
			+ "\t1h = 1HOUR\n"
			+ "\t2h = 2HOUR\n"
			+ "\t4h = 4HOUR\n"
			+ "\t6h = 6HOUR\n"
			+ "\t8h = 8HOUR\n"
			+ "\t12h = 12HOUR\n"
			+ "\t1d = 1DAY\n"
			+ "\t3d = 3DAY\n"
			+ "\t1w = 1WEEK\n"
			+ "\t1M = 1MONTH\n")
		sys.exit(1)

	else:
		main(sys.argv)
