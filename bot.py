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

#import ema
import ema2
import notify

from cfg import botCfg
from cfg import klineAPIIntervals

from util import cleanUp
from util import sigHandler
from util import auxPid_file_path
from util import auxCmd_pipe_file_path
from util import removePidFile
from util import daemonize

from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceWithdrawException, BinanceRequestException

# ----------------------------------------------------------------------------------------

class twttData:
	activated   = False
	apiKey      = ''
	apiSekKey   = ''
	accssTkn    = ''
	accssSekTkn = ''
	botId       = ''
	ntf         = object() # twitter data access

	def __init__(self):
		self.ntf = notify.ntfTwitter()
		self.activated = False

	def accessData(self, botIdP):
		self.apiKey      = os.getenv('TWITTER_APIKEY', 'NOTDEF')
		self.apiSekKey   = os.getenv('TWITTER_APISEKKEY', 'NOTDEF')
		self.accssTkn    = os.getenv('TWITTER_ACCSSTKN', 'NOTDEF')
		self.accssSekTkn = os.getenv('TWITTER_ACCSSSEKTKN', 'NOTDEF')
		self.botId       = botIdP

		if self.apiKey == 'NOTDEF' or self.apiSekKey == 'NOTDEF' or self.accssTkn == 'NOTDEF' or self.accssSekTkn == 'NOTDEF':
			return -1

		if self.ntf.auth(self.apiKey, self.apiSekKey, self.accssTkn, self.accssSekTkn) == False:
			return -1

		self.activated = True

		return 0

	def write(self, message):
		if self.activated == True:
			self.ntf.write(time.strftime("%Y-%m-%d %H:%M:%S ", time.gmtime()) + self.botId + " " + message)

class bot(Exception):

	cfg     = object()
	twtt    = object()
	emaSlow = object()
	emaFast = object()

	# -----------------------------------------------
	def __init__(self, pid : int, botId : str, binance_apikey : str, binance_sekkey : str,
	             work_path : str, pid_file_path : str, cmd_pipe_file_path : str, log_file : str,
	             binance_pair : str, fast_ema : int, fast_ema_offset : int, slow_ema : int,
	             slow_ema_offset: int, time_sample : int , notification):

		global auxPid_file_path
		global auxCmd_pipe_file_path

		auxPid_file_path      = pid_file_path
		auxCmd_pipe_file_path = cmd_pipe_file_path

		self.cfg = botCfg()

		self.cfg.set('binance_apikey'    , binance_apikey)
		self.cfg.set('binance_sekkey'    , binance_sekkey)
		self.cfg.set('work_path'         , work_path)
		self.cfg.set('pid'               , pid)
		self.cfg.set('pid_file_path'     , pid_file_path)
		self.cfg.set('cmd_pipe_file_path', cmd_pipe_file_path)
		self.cfg.set('log_file'          , log_file)
		self.cfg.set('binance_pair'      , binance_pair)
		self.cfg.set('fast_ema'          , fast_ema)
		self.cfg.set('fast_ema_offset'   , fast_ema_offset)
		self.cfg.set('slow_ema'          , slow_ema)
		self.cfg.set('slow_ema_offset'   , slow_ema_offset)

		self.twtt = twttData()

		self.emaSlow = ema2.ema(self.cfg.get('slow_ema'), self.cfg.get('slow_ema_offset'))
		self.emaFast = ema2.ema(self.cfg.get('fast_ema'), self.cfg.get('fast_ema_offset'))

		if notification.lower() == 'twitter':
			self.twtt.accessData(botId)

		try:
			self.cfg.set('time_sample', klineAPIIntervals[time_sample])

		except KeyError as e:
			logging.info(f'Error: time sample {argvInit[6]} not defined. Use one of: ')
			logging.info(klineAPIIntervals.keys())
			raise KeyError

		try:
			os.mkfifo(cmd_pipe_file_path)

		except OSError as e: 
			logging.info(f"Erro creating cmd pipe file: {e.errno} - {e.strerror}")
			raise OSError

		logging.info(f"\n================================================================\nBOT Configuration:")
		logging.info(f"\tPID = [{self.cfg.get('pid')}]")
		logging.info(f"\tPID file = [{self.cfg.get('pid_file_path')}]")
		logging.info(f"\tCMD pipe = [{self.cfg.get('cmd_pipe_file_path')}]")
		logging.info(f"\tWorking path = [{self.cfg.get('work_path')}]")
		logging.info(f"\tBinance pair = [{self.cfg.get('binance_pair')}]")
		logging.info(f"\tEMA Slow/Fast = [{self.cfg.get('slow_ema')} / {self.cfg.get('fast_ema')}]")
		logging.info(f"\tEMA Slow/Fast Offset = [{self.cfg.get('slow_ema_offset')} / {self.cfg.get('fast_ema_offset')}]")
		logging.info(f"\tTime sample = [{self.cfg.get('time_sample')}]")
		logging.info(f"\tBinance API key = [{self.cfg.get('binance_apikey')}]\n")

	# -----------------------------------------------
	def walletStatus(self) -> int:

		pair = self.cfg.get('binance_pair')

		logging.info("--- Wallet status ---")

		try:
			self.client = Client(self.cfg.get('binance_apikey'), self.cfg.get('binance_sekkey'), {"verify": True, "timeout": 20})

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
		if self.client.get_system_status()['status'] != 0:
			print('Binance out of service')
			return 4

		# 1 Pair wallet
		pair1 = self.client.get_asset_balance(pair[:3])
		logging.info(f'Symbol 1 on wallet: [' + pair[:3] + ']\tFree: [' + pair1['free'] + ']\tLocked: [' + pair1['locked'] + ']')

		# 2 Pair wallet
		pair2 = self.client.get_asset_balance(pair[3:])
		logging.info(f'Symbol 2 on wallet: [' + pair[3:] + ']\tFree: [' + pair2['free'] + ']\tLocked: [' + pair2['locked'] + ']')

		# Open orders
		openOrders = self.client.get_open_orders(symbol=pair)
		for openOrder in openOrders:
			logging.info(f'Order id [' + str(openOrder['orderId']) + '] data:\n' 
				+ '\tPrice.......: [' + openOrder['price']          + ']\n'
				+ '\tQtd.........: [' + openOrder['origQty']        + ']\n'
				+ '\tQtd executed: [' + openOrder['executedQty']    + ']\n'
				+ '\tSide........: [' + openOrder['side']           + ']\n'
				+ '\tType........: [' + openOrder['type']           + ']\n'
				+ '\tStop price..: [' + openOrder['stopPrice']      + ']\n'
				+ '\tIs working..: [' + str(openOrder['isWorking']) + ']')

		del pair
		del pair1
		del pair2
		del openOrders

		return 0

	# -----------------------------------------------
	def loadData(self) -> int:

		logging.info("--- Loading data ---")

		try:
			closedPrices = self.client.get_klines(symbol=self.cfg.get('binance_pair'), interval=self.cfg.get('time_sample'))
			'''
			[
				1499040000000,      # [ 0]Open time
				"0.01634790",       # [ 1]Open
				"0.80000000",       # [ 2]High
				"0.01575800",       # [ 3]Low
				"0.01577100",       # [ 4]Close
				"148976.11427815",  # [ 5]Volume
				1499644799999,      # [ 6]Close time
				"2434.19055334",    # [ 7]Quote asset volume
				308,                # [ 8]Number of trades
				"1756.87402397",    # [ 9]Taker buy base asset volume
				"28.46694368",      # [10]Taker buy quote asset volume
				"17928899.62484339" # [11]Can be ignored
			]
			'''

		except BinanceAPIException as e:
			logging.info(f'Binance API exception: {e.status_code} - {e.message}')
			return 1

		except BinanceRequestException as e:
			logging.info(f'Binance request exception: {e.status_code} - {e.message}')
			return 2

		except BinanceWithdrawException as e:
			logging.info(f'Binance withdraw exception: {e.status_code} - {e.message}')
			return 3

		# the last candle is running, so it will be descarded
		lastPrices = []
		[lastPrices.append(float(x[4])) for x in closedPrices[:-1]]

		try:
			if self.emaSlow.load(lastPrices) == False:
				logging.info(f"Error loading data for Slow EMA calculation ({self.cfg.get('slow_ema')}).")
				return 4
		except:
			logging.info("Exception loading EMA slow data!")
			return 6

		try:
			if self.emaFast.load(lastPrices) == False:
				logging.info(f"Error loading data for Slow EMA calculation ({self.cfg.get('slow_ema')}).")
				return 7
		except:
			logging.info("Exception loading EMA fast data!")
			return 8

		# TODO: send to twitter
		self.emaSlow.printData()
		self.emaFast.printData()

		del closedPrices
		del lastPrices

		logging.info("Ok!")

		return 0

	# -----------------------------------------------
	def start(self) -> int:

		logging.info("--- Starting ---")
		self.twtt.write('Bot Up!') 

		time_res = self.client.get_server_time()
		logging.info(f"Binance time: {time_res['serverTime']}")

		try:
			self.client.ping()
		except BinanceRequestException: 
			print('BinanceRequestException PING ERROR')
		except BinanceAPIExceptioan:
			print('BinanceAPIExceptioan PING ERROR')

		print('ok ping')

		time.sleep(10)

		return 0

		# Pair price
		"""
		try:
			getPrice = self.client.get_symbol_ticker(symbol=self.cfg.get('binance_pair'))

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

		botIteracSleepMin = 47 # Nyquist frequency for 1min
		msgNow            = ''

		self.runningBot = True
		self.calculatedSlowEMA = 0.0
		self.calculatedFastEMA = 0.0

		while self.runningBot:

			try:
				clast = self.client.get_klines(symbol=self.cfg.get('binance_pair'), interval=self.cfg.get('time_sample'))[-1:][0]

			except BinanceAPIException as e:
				logging.info(f'Binance API exception: {e.status_code} - {e.message}')
				return 4

			except BinanceRequestException as e:
				logging.info(f'Binance request exception: {e.status_code} - {e.message}')
				return 5

			except BinanceWithdrawException as e:
				logging.info(f'Binance withdraw exception: {e.status_code} - {e.message}')
				return 6

			currentRunningCandleTimeId = int(clast[6])
			currentRunningPrice = float(clast[4])

			logging.info(f'Value: [{currentRunningPrice}] | Time Id: [{currentRunningCandleTimeId}] | Last closed candle time id: [{self.savedLastCandleTimeId}]')

			if currentRunningCandleTimeId > self.savedLastCandleTimeId:
				# (enter here at first bot iteration)
				logging.info('CANDLE CLOSED (timeslice): Updating EMAs and Candle time ID:')

				self.savedLastCandleTimeId = currentRunningCandleTimeId

				self.calculatedSlowEMA = self.emaSlow.insertNewValueAndGetEMA(currentRunningPrice)
				self.calculatedFastEMA = self.emaFast.insertNewValueAndGetEMA(currentRunningPrice)

			else:
				# Candle not closed, just a forecast
				logging.info('Forecast EMA values:')
				self.calculatedSlowEMA = self.emaSlow.calculateNewValue(currentRunningPrice)
				self.calculatedFastEMA = self.emaFast.calculateNewValue(currentRunningPrice)
				continue

			logging.info(f'Slow EMA: [{self.calculatedSlowEMA}] | Fast EMA: [{self.calculatedFastEMA}]')

			if self.calculatedSlowEMA < self.calculatedFastEMA:
				msgNow = 'S (' + str(self.calculatedSlowEMA) + ') < F (' + str(self.calculatedFastEMA) + ') [[BUY]] (Now: ' + str(currentRunningPrice) + ')'
			elif self.calculatedSlowEMA > self.calculatedFastEMA:
				msgNow = 'S (' + str(self.calculatedSlowEMA) + ') > F (' + str(self.calculatedFastEMA) + ') [[SELL]] (Now: ' + str(currentRunningPrice) + ')'
			else:
				msgNow = 'S (' + str(self.calculatedSlowEMA) + ') = F (' + str(self.calculatedFastEMA) + ') [[HOLD ON]] (Now: ' + str(currentRunningPrice) + ')'

			logging.info(msgNow)
			self.twtt.write(msgNow)

			logging.info(f'Sleeping {botIteracSleepMin} secs...\n')
			time.sleep(botIteracSleepMin)

			del clast
			del getPrice

			return 0

		"""

# ----------------------------------------------------------------------------------------

def main(argv):
	ret = 0

	binance_apikey = os.getenv('BINANCE_APIKEY', 'NOTDEF_APIKEY')
	binance_sekkey = os.getenv('BINANCE_SEKKEY', 'NOTDEF_APIKEY')

	work_path          = argv[1]
	pid_file_path      = f'{argv[2]}_pid.text'
	cmd_pipe_file_path = f'{argv[2]}_pipecmd'
	log_file           = f'{argv[2]}_log.text'
	binance_pair       = argv[3]
	fast_ema           = int(argv[4])
	fast_ema_offset    = int(argv[5])
	slow_ema           = int(argv[6])
	slow_ema_offset    = int(argv[7])
	time_sample        = argv[8]

	pid = daemonize(work_path)

	f = open(pid_file_path, 'w+')
	f.write(f"{pid}\n{cmd_pipe_file_path}\n{log_file}\n{work_path}\n{binance_pair}\n")
	f.close()

	signal.signal(signal.SIGILL, sigHandler)
	signal.signal(signal.SIGTRAP, sigHandler)
	signal.signal(signal.SIGINT, sigHandler)
	signal.signal(signal.SIGHUP, sigHandler)
	signal.signal(signal.SIGTERM, sigHandler)
	signal.signal(signal.SIGSEGV, sigHandler)

	logging.basicConfig(filename=log_file, filemode='a', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y%m%d%H%M%S')

#	except IOError:
#		sys.stderr.write(f"Creating log file failed: {e.errno} - {e.strerror}\n")
#		sys.exit(1)


#	try:
#		CMD_PIPE_FILE = open(CMD_PIPE_FILE_PATH, "r")

#	except IOError:
#		sys.stderr.write(f"Opeing cmd pipe file failed: {e.errno} - {e.strerror}\n")
# 		sys.exit(1)

#	ret = runBot(logFile, BINANCE_PAIR, binance_apiKey, binance_sekKey)

	try:
		bot1 = bot(pid, argv[2],
		           binance_apikey, binance_sekkey,
		           work_path, pid_file_path, cmd_pipe_file_path,
		           log_file,
		           binance_pair,
		           fast_ema, fast_ema_offset,
		           slow_ema, slow_ema_offset,
					  time_sample,
		           argv[9])
	except:
		logging.info(f"BOT initialization error!")
		logging.shutdown()
		cleanUp(pid_file_path, cmd_pipe_file_path)
		sys.exit(1)

	else:

		ret = bot1.walletStatus()
		if ret != 0:
			logging.info(f"BOT wallet status return ERROR: [{ret}]")
			sys.exit(ret)

		ret = bot1.loadData()
		if ret != 0:
			logging.info(f"BOT load data return ERROR: [{ret}]")
			sys.exit(ret)

		ret = bot1.start()
		if ret != 0:
			logging.info(f"BOT start return ERROR: [{ret}]")
			sys.exit(ret)

#	CMD_PIPE_FILE.close()
	finally:
		logging.info(f"BOT return: [{ret}]")
		logging.shutdown()
		cleanUp(pid_file_path, cmd_pipe_file_path)
		sys.exit(ret)

if __name__ == '__main__':

	if len(sys.argv) != 10:
		print(f"Usage:\n\t{sys.argv[0]} <WORK_PATH> <BOT_ID> <BINANCE_PAIR> <FAST_EMA> <OFFSET_FAST_EMA> <SLOW_EMA> <OFFSET_SLOW_EMA> <TIME_SAMPLE> <NOTIFY>\nSample:\n\t{sys.argv[0]} ./ BOT1 BNBBTC 9 0 21 +4 30m twitter\n\n")
		print("You must define the environment variables with yours:\t\n"
			+ "\t BINANCE_APIKEY = Binance API key\n"
			+ "\t BINANCE_SEKKEY = Binance Security key\n\n")
		print("Where <TIME_SAMPLE>:\n"
			+ "\t1m  = 1MINUTE\n"
			+ "\t3m  = 3MINUTE\n"
			+ "\t5m  = 5MINUTE\n"
			+ "\t15m = 15MINUTE\n"
			+ "\t30m = 30MINUTE\n"
			+ "\t1h  = 1HOUR\n"
			+ "\t2h  = 2HOUR\n"
			+ "\t4h  = 4HOUR\n"
			+ "\t6h  = 6HOUR\n"
			+ "\t8h  = 8HOUR\n"
			+ "\t12h = 12HOUR\n"
			+ "\t1d  = 1DAY\n"
			+ "\t3d  = 3DAY\n"
			+ "\t1w  = 1WEEK\n"
			+ "\t1M  = 1MONTH\n"
			+ "<NOTIFY>:\n"
			+ "\tlog     = Writes calls to file log\n"
			+ "\ttwitter = Writes calls to Twitter. You must define the environment variables with yours:\n"
			+ "\t\tTWITTER_APIKEY      = Consumer API keys: API key\n"
			+ "\t\tTWITTER_APISEKKEY   = Consumer API keys: API security key\n"
			+ "\t\tTWITTER_ACCSSTKN    = Access token and access token secret: Access token\n"
			+ "\t\tTWITTER_ACCSSSEKTKN = Access token and access token secret: Access security token\n")
		sys.exit(1)

	else:
		main(sys.argv)
