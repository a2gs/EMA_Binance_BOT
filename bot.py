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

#runningBot = True # Used to stop/start bot main loop (cmds from pipe file)

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

# ----------------------------------------------------------------------------------------

def cleanUp(pid_file_path, cmd_pipe_file_path):
	os.remove(pid_file_path)
	os.remove(cmd_pipe_file_path)

def sigHandler(signum, frame):
	sys.stderr.write(f'Singal {signum} received\n')
	logging.info(f'Singal {signum} received\n')
	logging.shutdown()
	sys.exit(0)

auxPid_file_path = ''
auxCmd_pipe_file_path = ''

def removePidFile():
	global auxPid_file_path
	global auxCmd_pipe_file_path

	cleanUp(auxPid_file_path, auxCmd_pipe_file_path)

def daemonize(work_path):
	pid_num = 0

	try:
		pid_num = os.fork()
		if pid_num > 0:
			sys.exit(0)

	except OSError as e:
		sys.stderr.write(f"Fork failed: {e.errno} - {e.strerror}\n")
		sys.exit(1)

	os.chdir(work_path)
	os.setsid()
	os.umask(0)

	atexit.register(removePidFile)

	return(os.getpid())

# ----------------------------------------------------------------------------------------

class EMAOffsetQueue:
	offset   = int()
	topo     = int()
	elements = list()
	element  = float()

	def __init__(self, offsetX):
		self.offset = offsetX
		self.topo = 0

		self.element = 0.0
		self.elements = []

	def insertN(self, n):
		if self.offset == 0:
			self.element = n
		else:
			self.elements.append(n)
   
		if self.topo == self.offset:
			self.elements.pop(0)
		else:
			self.topo = self.topo + 1

	def getN(self):
		if self.offset == 0:
			return(self.element)
   
		return(self.elements[self.topo])
   
	def getAll(self):
		if self.offset == 0:
			return(self.element)
   
		return(self.elements)

class ema:
	emaValue    = 0
	ema         = 0.0
	k           = 0
	seed        = 0.0
	offset      = object()

	def __init__(self, emaValue, ema_initPopulation, offsetValue):

# TODO: throw a exception:
#		if emaValue < len(ema_initPopulation):
#			return False

		self.k = 2 / (emaValue + 1)
		self.emaValue = emaValue

		# First 'emaValue's are simple moving avarage
		self.ema = sum(ema_initPopulation[:emaValue]) / emaValue

		# Other values are EMA calculations
		[self.insertNewValue(x) for x in ema_initPopulation[emaValue:]]

		self.offset = EMAOffsetQueue(offsetValue)

	def getCurrent(self):
		return(self.ema)

	def insertNewValue(self, new):
		self.ema = ((new - self.ema) * self.k) + self.ema

	def insertNewValueAndGetEMA(self, new):
		self.insertNewValue(new)
		return(self.getCurrent())

	def forecastValue(self, new):
		ret = ((new - self.ema) * self.k) + self.ema
		return(ret)

class bot(Exception):

	savedLastCandleTimeId = int(0)
	calculatedSlowEMA     = float(0.0)
	calculatedFastEMA     = float(0.0)
	runningBot            = True
	cfg                   = object()

	def __init__(self, pid, binance_apikey, binance_sekkey, work_path, pid_file_path, cmd_pipe_file_path, log_file, binance_pair, fast_ema, fast_ema_offset, slow_ema, slow_ema_offset, time_sample):
		self.cfg = botCfg()

		global auxPid_file_path
		global auxCmd_pipe_file_path

		auxPid_file_path      = pid_file_path
		auxCmd_pipe_file_path = cmd_pipe_file_path

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

		try:
			self.cfg.set('time_sample', klineAPIIntervals[time_sample])

		except KeyError as e:
			logging.info(f'Error: time sample {argvInit[6]} not defined. Use one of: ')
			logging.info(klineAPIIntervals.keys())
			raise

		try:
			os.mkfifo(cmd_pipe_file_path)

		except OSError as e: 
			logging.info(f"Erro creating cmd pipe file: {e.errno} - {e.strerror}")
			raise

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

		self.savedLastCandleTimeId = 0
		self.calculatedSlowEMA     = 0.0
		self.calculatedFastEMA     = 0.0
		self.runningBot            = True

	def walletStatus(self):

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
	
		# TODO: call 'del' below with 'finally:' exception control (there are more places like this)

		# Exchange status
		if self.client.get_system_status()['status'] != 0:
			print('Binance out of service')
			return 1

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
		del openOrder
		del openOrders

		return 0

	def loadData(self):

		logging.info("--- Loading data ---")

		lastPrices = []

		slow_emaAux = self.cfg.get('slow_ema')
		fast_emaAux = self.cfg.get('fast_ema')
		slow_offset = self.cfg.get('slow_ema_offset')
		fast_offset = self.cfg.get('fast_ema_offset')
		
#		if slow_offset < fast_offset:
#			biggest_offset = fast_offset
#		else:
#			biggest_offset = slow_offset

		# the last candle is running, so it will be descarded
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

		try:
			closedPrices = self.client.get_klines(symbol=self.cfg.get('binance_pair'), interval=self.cfg.get('time_sample'))[:-1]

		except BinanceAPIException as e:
			logging.info(f'Binance API exception: {e.status_code} - {e.message}')
			return 1

		except BinanceRequestException as e:
			logging.info(f'Binance request exception: {e.status_code} - {e.message}')
			return 2

		except BinanceWithdrawException as e:
			logging.info(f'Binance withdraw exception: {e.status_code} - {e.message}')
			return 3

		[lastPrices.append(float(x[4])) for x in closedPrices]

#		print('return closedPrices:')
#		print(closedPrices)
#		print(len(closedPrices))
#		print('---')
#		print("Prices:")
#		print(lastPrices)
#		print("Prices len:")
#		print(len(lastPrices))

		self.emaSlow = ema(slow_emaAux, lastPrices, slow_offset)
		self.emaFast = ema(fast_emaAux, lastPrices, fast_offset)

		self.savedLastCandleTimeId = int(closedPrices[-2:][0][6])

		logging.info(f'Last CLOSED candle time: {self.savedLastCandleTimeId}')

		del lastPrices
		del closedPrices
		del slow_emaAux
		del fast_emaAux
		del slow_offset
		del fast_offset
#		del biggest_offset

		logging.info(f'Initial slow EMA {self.emaSlow.getCurrent()} | Initial fast EMA {self.emaFast.getCurrent()}')

		return 0

# ---------
	def start(self):
		logging.info("--- Stating ---")

		# Pair price
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

		self.runningBot = True
		self.calculatedSlowEMA = 0.0
		self.calculatedFastEMA = 0.0

		while self.runningBot:

			try:
				clast = self.client.get_klines(symbol=self.cfg.get('binance_pair'), interval=self.cfg.get('time_sample'))[-1:][0]

			except BinanceAPIException as e:
				logging.info(f'Binance API exception: {e.status_code} - {e.message}')
				return 1

			except BinanceRequestException as e:
				logging.info(f'Binance request exception: {e.status_code} - {e.message}')
				return 2

			except BinanceWithdrawException as e:
				logging.info(f'Binance withdraw exception: {e.status_code} - {e.message}')
				return 3

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
				self.calculatedSlowEMA = self.emaSlow.forecastValue(currentRunningPrice)
				self.calculatedFastEMA = self.emaSlow.forecastValue(currentRunningPrice)

			logging.info(f'Slow EMA: [{self.calculatedSlowEMA}] | Fast EMA: [{self.calculatedFastEMA}]')

			if self.calculatedSlowEMA < self.calculatedFastEMA:
				logging.info('S<F [[BUY]]')
			elif self.calculatedSlowEMA > self.calculatedFastEMA:
				logging.info('S>F [[SELL]]')
			else:
				logging.info('S=F [[HOLD ON]]')

			logging.info(f'Sleeping {botIteracSleepMin} secs...\n')
			time.sleep(botIteracSleepMin)

		return 0


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
		bot1 = bot(pid,
		           binance_apikey, binance_sekkey,
		           work_path, pid_file_path, cmd_pipe_file_path,
		           log_file,
		           binance_pair,
		           fast_ema, fast_ema_offset,
		           slow_ema, slow_ema_offset,
					  time_sample)
	except:
		logging.info(f"BOT initialization error!")
		logging.shutdown()
		cleanUp(pid_file_path, cmd_pipe_file_path)
		sys.exit(1)

	else:

		ret = bot1.walletStatus()
		if ret != 0:
			logging.info(f"BOT wallet status return ERROR: [{ret}]")
			logging.shutdown()
			cleanUp(pid_file_path, cmd_pipe_file_path)
			sys.exit(ret)

		ret = bot1.loadData()
		if ret != 0:
			logging.info(f"BOT load data return ERROR: [{ret}]")
			logging.shutdown()
			cleanUp(pid_file_path, cmd_pipe_file_path)
			sys.exit(ret)

		ret = bot1.start()
		if ret != 0:
			logging.info(f"BOT start return ERROR: [{ret}]")
			logging.shutdown()
			cleanUp(pid_file_path, cmd_pipe_file_path)
			sys.exit(ret)

		logging.info(f"BOT return: [{ret}]")

#	CMD_PIPE_FILE.close()
	logging.shutdown()
	cleanUp(pid_file_path, cmd_pipe_file_path)
	sys.exit(ret)

if __name__ == '__main__':

	if len(sys.argv) != 9:
		print(f"Usage:\n\t{sys.argv[0]} <WORK_PATH> <BOT_ID> <BINANCE_PAIR> <FAST_EMA> <OFFSET_FAST_EMA> <SLOW_EMA> <OFFSET_SLOW_EMA> <TIME_SAMPLE>\nSample:\n\t{sys.argv[0]} ./ BOT1 BNBBTC 9 0 21 +4 30m\n")
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
