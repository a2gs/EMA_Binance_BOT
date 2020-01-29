#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Andre Augusto Giannotti Scota
# andre.scota@gmail.com
# MIT license

import sys
import errno
import signal
from os import mkfifo, getenv
from time import sleep, strftime, gmtime
from logging.handlers import logging, RotatingFileHandler

import ema2
import notify
from cfg import botCfg, klineAPIIntervals
from util import cleanUp, sigHandler, auxPid_file_path, auxCmd_pipe_file_path, removePidFile, daemonize

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
		self.apiKey      = getenv('TWITTER_APIKEY', 'NOTDEF')
		self.apiSekKey   = getenv('TWITTER_APISEKKEY', 'NOTDEF')
		self.accssTkn    = getenv('TWITTER_ACCSSTKN', 'NOTDEF')
		self.accssSekTkn = getenv('TWITTER_ACCSSSEKTKN', 'NOTDEF')
		self.botId       = botIdP

		if self.apiKey == 'NOTDEF' or self.apiSekKey == 'NOTDEF' or self.accssTkn == 'NOTDEF' or self.accssSekTkn == 'NOTDEF':
			return -1

		if self.ntf.auth(self.apiKey, self.apiSekKey, self.accssTkn, self.accssSekTkn) == False:
			return -1

		self.activated = True

		return 0

	def write(self, message):
		if self.activated == True:
			self.ntf.write(strftime("%Y-%m-%d %H:%M:%S ", gmtime()) + self.botId + " " + message)

class bot(Exception):

	lastPrice  = 0
	lastStatus = 0
	cfg        = 0
	twtt       = 0
	emaSlow    = 0
	emaFast    = 0

	# -----------------------------------------------
	def __init__(self):

		self.lastPrice  = float(0.0)
		self.lastStatus = 0
		self.emaSlow    = object()
		self.emaFast    = object()
		self.cfg        = botCfg()
		self.twtt       = twttData()

	# -----------------------------------------------
	def loadCfg(self,
	            pid : int,
	            botId : str,
	            binance_apikey : str,
	            binance_sekkey : str,
	            work_path : str,
	            pid_file_path : str,
	            cmd_pipe_file_path : str,
	            binance_pair : str,
	            fast_ema : int,
	            fast_ema_offset : int,
	            slow_ema : int,
	            slow_ema_offset: int,
	            time_sample : int,
	            notification : str,
	            max_timeout_to_exit : int,
	            retry_timeout : int ) -> int:

		global auxPid_file_path
		global auxCmd_pipe_file_path

		auxPid_file_path      = pid_file_path
		auxCmd_pipe_file_path = cmd_pipe_file_path

		self.cfg.set('binance_apikey'     , binance_apikey)
		self.cfg.set('binance_sekkey'     , binance_sekkey)
		self.cfg.set('work_path'          , work_path)
		self.cfg.set('pid'                , pid)
		self.cfg.set('pid_file_path'      , pid_file_path)
		self.cfg.set('bot_id'             , botId)
		self.cfg.set('cmd_pipe_file_path' , cmd_pipe_file_path)
		self.cfg.set('binance_pair'       , binance_pair)
		self.cfg.set('fast_ema'           , fast_ema)
		self.cfg.set('fast_ema_offset'    , fast_ema_offset)
		self.cfg.set('slow_ema'           , slow_ema)
		self.cfg.set('slow_ema_offset'    , slow_ema_offset)
		self.cfg.set('max_timeout_to_exit', max_timeout_to_exit)
		self.cfg.set('retry_timeout'      , retry_timeout)

		self.emaSlow = ema2.ema(self.cfg.get('slow_ema'), self.cfg.get('slow_ema_offset'))
		self.emaFast = ema2.ema(self.cfg.get('fast_ema'), self.cfg.get('fast_ema_offset'))

		if notification.lower() == 'twitter':
			self.twtt.accessData(self.cfg.get('bot_id'))

		try:
			self.cfg.set('time_sample', klineAPIIntervals[time_sample])

		except KeyError as e:
			logging.info(f'Error: time sample {argvInit[6]} not defined. Use one of: ')
			logging.info(klineAPIIntervals.keys())
			raise

		try:
			mkfifo(cmd_pipe_file_path)

		except OSError as e: 
			logging.info(f"Erro creating cmd pipe file: {e.errno} - {e.strerror}")
			raise

		logging.info(f"\n================================================================\nBOT {self.cfg.get('bot_id')} Configuration:")
		logging.info(f"\tPID = [{self.cfg.get('pid')}]")
		logging.info(f"\tPID file = [{self.cfg.get('pid_file_path')}]")
		logging.info(f"\tCMD pipe = [{self.cfg.get('cmd_pipe_file_path')}]")
		logging.info(f"\tWorking path = [{self.cfg.get('work_path')}]")
		logging.info(f"\tBinance pair = [{self.cfg.get('binance_pair')}]")
		logging.info(f"\tEMA Slow/Fast = [{self.cfg.get('slow_ema')} / {self.cfg.get('fast_ema')}]")
		logging.info(f"\tEMA Slow/Fast Offset = [{self.cfg.get('slow_ema_offset')} / {self.cfg.get('fast_ema_offset')}]")
		logging.info(f"\tTime sample = [{self.cfg.get('time_sample')}]")
		logging.info(f"\tBinance API key = [{self.cfg.get('binance_apikey')}]")
		logging.info(f"\tMaximum timeout attempts before exit = [{self.cfg.get('max_timeout_to_exit')}]")
		logging.info(f"\tSeconds between timeouts = [{self.cfg.get('retry_timeout')}]\n")
		return 0

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

		self.lastPrice = float(closedPrices[-1][4]) # Saving last candle lcose price

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

		del closedPrices
		del lastPrices

		logging.info("Ok!")

		return 0

	# -----------------------------------------------
	def logAndNotif(self, msg : str):
		self.twtt.write(msg)
		logging.info(msg)

	# -----------------------------------------------
	def start(self) -> int:

		logging.info("--- Starting ---")

		infotwtS = {}
		infotwtF = {}

		infotwtS = self.emaSlow.info()
		infotwtF = self.emaFast.info()

		self.logAndNotif(f"Bot Up! {self.cfg.get('binance_pair')} | {self.cfg.get('time_sample')} | EMAs: Slow[{infotwtS['period']}:{infotwtS['offset']}:{infotwtS['current']}] Fast[{infotwtF['period']}:{infotwtF['offset']}:{infotwtF['current']}]")

		del infotwtF
		del infotwtS

		# ############# #
		# BOT MAIN LOOP #
		# ############# #

		# Last status:
		# 1 - BUY
		# 2 - SELL
		# 3 - HOLD
		self.lastStatus = 0 # 'Forcing' (0 to 'x') a notification at startup

		savedLastOpenCandle   = 0
		savedLastClosedCandle = 0
		timeOutCounter        = 0

		while True:

			logging.info("pinging...")
			try:
				self.client.ping()
			except: 
				timeOutCounter = timeOutCounter + 1

				if timeOutCounter >= self.cfg.get('max_timeout_to_exit'):
					self.logAndNotif(f"BOT EXIT! MAX TIMEOUT REACHED ({self.cfg.get('max_timeout_to_exit')})!")
					return 1 # MAX TIMEOUT REACHED

				self.logAndNotif(f"PING ERROR! Attempt {timeOutCounter} of {self.cfg.get('max_timeout_to_exit')}. Waiting {self.cfg.get('retry_timeout')} seconds...")

				sleep(self.cfg.get('retry_timeout')) # wait a little to next ping

				logging.info("retry")

				continue

			timeOutCounter = 0

			sleep(0.5)

			lastCandle = self.client.get_klines(symbol=self.cfg.get('binance_pair'), interval=self.cfg.get('time_sample'), limit=1)

			lastCandleOpenTime  = int(lastCandle[0][0])
			lastCandleCloseTime = int(lastCandle[0][6])

			self.lastPrice = float(lastCandle[0][4])

#			currentTime = int(self.client.get_server_time()['serverTime'])
#			logging.info(f"candle and server time: {savedLastOpenCandle}={lastCandleOpenTime} | {currentTime} | {savedLastClosedCandle}={lastCandleCloseTime}")

			# Running upon last candle time or is it a new?
			if savedLastOpenCandle != lastCandleOpenTime and savedLastClosedCandle != lastCandleCloseTime:

				savedLastOpenCandle   = lastCandleOpenTime
				savedLastClosedCandle = lastCandleCloseTime

				slow = self.emaSlow.calcNewValueIsertAndPop(self.lastPrice)
				fast = self.emaFast.calcNewValueIsertAndPop(self.lastPrice)

				if slow < fast:
					if self.lastStatus != 1:
						self.lastStatus = 1
						self.logAndNotif(f"BUY (slow {slow} < {fast} fast)")

				elif slow > fast:
					if self.lastStatus != 2:
						self.lastStatus = 2
						self.logAndNotif(f"SELL (slow {slow} > {fast} fast)")

				else:
					self.logAndNotif(f"HOLD (slow {slow} = {fast} fast)")
					self.lastStatus = 3

			sleep(0.5)

		return 0

# ----------------------------------------------------------------------------------------

def main(argv):
	ret = int(0)

	pid_file_path      = f'{argv[2]}_pid.text'
	cmd_pipe_file_path = f'{argv[2]}_pipecmd'
	log_file           = f'{argv[2]}_log.text'

	pid = daemonize(argv[1])

	f = open(pid_file_path, 'w+')
	f.write(f"{pid}\n{cmd_pipe_file_path}\n{log_file}\n{argv[1]}\n{argv[3]}\n")
	f.close()

	signal.signal(signal.SIGILL , sigHandler)
	signal.signal(signal.SIGTRAP, sigHandler)
	signal.signal(signal.SIGINT , sigHandler)
	signal.signal(signal.SIGHUP , sigHandler)
	signal.signal(signal.SIGTERM, sigHandler)
	signal.signal(signal.SIGSEGV, sigHandler)

	logging.basicConfig(handlers = [ RotatingFileHandler(log_file, maxBytes = int(argv[10]), backupCount = int(argv[11])) ],
	                    level    = logging.INFO,
	                    format   = '%(asctime)s - %(levelname)s - %(message)s',
	                    datefmt  = '%Y%m%d%H%M%S')

#	except IOError:
#		sys.stderr.write(f"Creating log file failed: {e.errno} - {e.strerror}\n")
#		sys.exit(1)

#	try:
#		CMD_PIPE_FILE = open(CMD_PIPE_FILE_PATH, "r")

#	except IOError:
#		sys.stderr.write(f"Opeing cmd pipe file failed: {e.errno} - {e.strerror}\n")
# 		sys.exit(1)

#	ret = runBot(logFile, BINANCE_PAIR, binance_apiKey, binance_sekKey)

	bot1 = bot()

	try:
		bot1.loadCfg(pid                 = pid,
		             botId               = argv[2],
		             binance_apikey      = getenv('BINANCE_APIKEY', 'NOTDEF_APIKEY'),
		             binance_sekkey      = getenv('BINANCE_SEKKEY', 'NOTDEF_APIKEY'),
		             work_path           = argv[1],
		             pid_file_path       = pid_file_path,
		             cmd_pipe_file_path  = cmd_pipe_file_path,
		             binance_pair        = argv[3],
		             fast_ema            = int(argv[4]),
		             fast_ema_offset     = int(argv[5]),
		             slow_ema            = int(argv[6]),
		             slow_ema_offset     = int(argv[7]),
		             time_sample         = argv[8],
		             notification        = argv[9],
		             max_timeout_to_exit = int(argv[12]),
		             retry_timeout       = int(argv[13]) )

	except:
		endBot(1, "BOT initialization error!")

	try:
		ret = bot1.walletStatus()
		if ret != 0:
			endBot(ret, f"BOT wallet status return ERROR: [{ret}]")

		ret = bot1.loadData()
		if ret != 0:
			endBot(ret, f"BOT load data return ERROR: [{ret}]")

		ret = bot1.start()
		if ret != 0:
			endBot(ret, f"BOT start return ERROR: [{ret}]")

	except:
		endBot(ret, f"BOT EXCEPTION! Exit..")

#	CMD_PIPE_FILE.close()
	endBot(ret, f"BOT return: [{ret}]")

def endBot(code : int, msg : str):
	logging.info(msg)
	logging.shutdown()
	cleanUp(pid_file_path, cmd_pipe_file_path)
	sys.exit(code)

if __name__ == '__main__':

	if len(sys.argv) != 14:
		print(f"Usage:\n\t{sys.argv[0]} <WORK_PATH> <BOT_ID> <BINANCE_PAIR> <FAST_EMA> <OFFSET_FAST_EMA> <SLOW_EMA> <OFFSET_SLOW_EMA> <TIME_SAMPLE> <NOTIFY> <MAX_BYE_LOG_SIZE> <LOG_N_ROTATION> <RETRY_TIMEOUT> <MAX_TIMEOUT_TO_EXIT>\nSample:\n\t{sys.argv[0]} ./ BOT1 BNBBTC 9 0 21 +4 30m twitter 1000000 2 10 100\n\n")
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
