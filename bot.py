#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Andre Augusto Giannotti Scota
# andre.scota@gmail.com
# MIT license

from sys import argv, exit
from signal import signal, SIGILL, SIGTRAP, SIGINT, SIGHUP, SIGTERM, SIGSEGV
from os import mkfifo, getenv
from time import sleep, strftime, gmtime
from logging.handlers import logging, RotatingFileHandler

from ema import ema
import notify
from cfg import botCfg, klineAPIIntervals
from util import sigHandler, setPidFileAndPipeFile, removePidFile, daemonize, completeMilliTime

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

	cfg             = 0
	twtt            = 0
	emaSlow         = 0
	emaFast         = 0
	lastOpenTime    = 0
	lastCloseTime   = 0
	client          = 0

	# -----------------------------------------------
	def __init__(self):

		self.emaSlow         = object()
		self.emaFast         = object()
		self.client          = object()
		self.cfg             = botCfg()
		self.twtt            = twttData()
		self.lastOpenTime    = 0
		self.lastCloseTime   = 0

	# -----------------------------------------------
	def loadCfg(self,
	            pid                 : int,
	            botId               : str,
	            binance_apikey      : str,
	            binance_sekkey      : str,
	            work_path           : str,
	            pid_file_path       : str,
	            cmd_pipe_file_path  : str,
	            binance_pair        : str,
	            fast_ema            : int,
	            fast_ema_offset     : int,
	            slow_ema            : int,
	            slow_ema_offset     : int,
	            time_sample         : int,
	            notification        : str,
	            max_timeout_to_exit : int,
	            retry_timeout       : int ) -> int:

#		global auxPid_file_path
#		global auxCmd_pipe_file_path

#		auxPid_file_path      = pid_file_path
#		auxCmd_pipe_file_path = cmd_pipe_file_path
		setPidFileAndPipeFile(pid_file_path, cmd_pipe_file_path)

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

		self.emaSlow = ema(self.cfg.get('slow_ema'), self.cfg.get('slow_ema_offset'))
		self.emaFast = ema(self.cfg.get('fast_ema'), self.cfg.get('fast_ema_offset'))

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

		except (OSError, FileExistsError) as e: 
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
		logging.info(f"\tTime sample = [{self.cfg.get('time_sample')[0]}]")
		logging.info(f"\tBinance API key = [{self.cfg.get('binance_apikey')}]")
		logging.info(f"\tMaximum timeout attempts before exit = [{self.cfg.get('max_timeout_to_exit')}]")
		logging.info(f"\tSeconds between timeouts = [{self.cfg.get('retry_timeout')}]\n")
		return 0

	# -----------------------------------------------
	def connectBinance(self) -> int:

		try:
			self.client = Client(self.cfg.get('binance_apikey'), self.cfg.get('binance_sekkey'), {"verify": True, "timeout": 20})

		except BinanceAPIException as e:
			logging.info(f'Binance API exception: Status code: [{e.status_code}] | Response: [{e.response}] | Code: [{e.code}] | Msg: [{e.message}] | Request: [{e.request}]')
			return 1

		except BinanceRequestException as e:
			logging.info(f'Binance request exception: {e.status_code} - {e.message}')
			return 2

		except BinanceWithdrawException as e:
			logging.info(f'Binance withdraw exception: {e.status_code} - {e.message}')
			return 3

		except Exception as e:
			logging.info(f"Binance unknow exception: {e}")
			return 4
	
		# Exchange status
		if self.client.get_system_status()['status'] != 0:
			logging.info('Binance out of service')
			return 5

		return 0

	def walletStatus(self) -> int:

		pair = self.cfg.get('binance_pair')

		logging.info("--- Wallet status ---")

		# 1 Pair wallet
		pair1 = self.client.get_asset_balance(pair[:3])
		logging.info(f'Symbol 1 on wallet: [' + pair[:3] + ']\tFree: [' + pair1['free'] + ']\tLocked: [' + pair1['locked'] + ']')

		# 2 Pair wallet
		pair2 = self.client.get_asset_balance(pair[3:])
		logging.info(f'Symbol 2 on wallet: [' + pair[3:] + ']\tFree: [' + pair2['free'] + ']\tLocked: [' + pair2['locked'] + ']')

		# Open orders
		'''
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

		del openOrders
		'''

		del pair
		del pair1
		del pair2

		return 0

	# -----------------------------------------------
	def loadData(self) -> int:

		logging.info("--- Loading data ---")

		try:
			closedPrices = self.client.get_klines(symbol = self.cfg.get('binance_pair'), interval = self.cfg.get('time_sample')[0])
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
			logging.info(f'Binance API exception: Status code: [{e.status_code}] | Response: [{e.response}] | Code: [{e.code}] | Msg: [{e.message}] | Request: [{e.request}]')
			return 1

		except BinanceRequestException as e:
			logging.info(f'Binance request exception: {e.status_code} - {e.message}')
			return 2

		except BinanceWithdrawException as e:
			logging.info(f'Binance withdraw exception: {e.status_code} - {e.message}')
			return 3

		except Exception as e:
			logging.info(f"Binance unknow exception: {e}")
			return 4

		self.lastOpenTime  = closedPrices[-1][0]
		self.lastCloseTime = closedPrices[-1][6]
		logging.info(f"Last candle (running) open time.: [{self.lastOpenTime}]")
		logging.info(f"Last candle (running) close time: [{self.lastCloseTime}]")

		# the last candle is running, so it will be descarded (it is not closed!)
		lastPrices = []
		try:
			[lastPrices.append(float(x[4])) for x in closedPrices[:-1]]
		except Exception as e:
			logging.info(f"Exception loading EMAs data: {e}")
			return 9

		try:
			if self.emaSlow.load(lastPrices) == False:
				logging.info(f"Error loading data for Slow EMA calculation ({self.cfg.get('slow_ema')}).")
				return 10
		except Exception as e:
			logging.info(f"Exception loading EMA slow data: {e}")
			return 11

		try:
			if self.emaFast.load(lastPrices) == False:
				logging.info(f"Error loading data for Fast EMA calculation ({self.cfg.get('fast_ema')}).")
				return 12
		except Exception as e:
			logging.info(f"Exception loading EMA fast data: {e}")
			return 13

		infotwtS = {}
		infotwtF = {}

		infotwtS = self.emaSlow.info()
		infotwtF = self.emaFast.info()

		self.logAndNotif(f"Bot Up! {self.cfg.get('binance_pair')} | {self.cfg.get('time_sample')[0]} | EMAs: Slow[{infotwtS['period']}:{infotwtS['offset']}:{infotwtS['current']}] Fast[{infotwtF['period']}:{infotwtF['offset']}:{infotwtF['current']}]")

		logging.info("Ok!")

		del closedPrices
		del lastPrices
		del infotwtF
		del infotwtS

		return 0

	# -----------------------------------------------
	def logAndNotif(self, msg : str):
		self.twtt.write(msg)
		logging.info(msg)

	# -----------------------------------------------
	def start(self) -> int:

		logging.info("--- Starting ---")

		# Last status:
		# 0 - 'Forcing' (0 to 'x') a notification at startup
		# 1 - BUY
		# 2 - SELL
		lastStatus = 0

		last2Candles = object()
		currentTime  = int(0)
		lastPrice    = float(0.0)
		slowEMA      = float(0.0)
		fastEMA      = float(0.0)

		while True: # main loop

			while True:

				try:
					currentTime = self.client.get_server_time()['serverTime']

				except BinanceAPIException as e:
					logging.info(f'Binance API get_server_time exception: {e.status_code} - {e.message}')
					return 1

				except BinanceRequestException as e:
					logging.info(f'Binance request get_server_time exception: {e.status_code} - {e.message}')
					return 2

				except BinanceWithdrawException as e:
					logging.info('Binance withdraw get_server_time exception.')
					return 3

				except Exception as e:
					logging.info(f'Binance get_server_time exception: {e}')
					return 4

				logging.info(f"Binance time....................: [{currentTime}]")
				logging.info(f"Last candle (running) open time.: [{self.lastOpenTime}]")
				logging.info(f"Last candle (running) close time: [{self.lastCloseTime}]")

				if self.lastOpenTime < currentTime < self.lastCloseTime:
					logging.info("sleeping 2 sec .... TODO a better sleep time")
					sleep(2)
				else:
					logging.info("CLOSED CANDLE!")
					break

			try:
				last2Candles = self.client.get_klines(symbol   = self.cfg.get('binance_pair'),
				                                      interval = self.cfg.get('time_sample')[0],
				                                      limit    = 2)

			except BinanceAPIException as e:
				logging.info(f'Binance API get_klines exception: {e.status_code} - {e.message}')
				return 5

			except BinanceRequestException as e:
				logging.info(f'Binance request get_klines exception: {e.status_code} - {e.message}')
				return 6

			except BinanceWithdrawException as e:
				logging.info(f'Binance withdraw get_klines exception: {e.status_code} - {e.message}')
				return 7

			except Exception as e:
				logging.info(f'Binance get_klines exception: {e}')
				return 8

			self.lastOpenTime  = last2Candles[1][0]
			self.lastCloseTime = last2Candles[1][6]

			lastPrice = float(last2Candles[0][4])

			self.emaSlow.calcNewValueInsertAndPop(lastPrice)
			self.emaFast.calcNewValueInsertAndPop(lastPrice)

			try:
				slowEMA = self.emaSlow.getWithOffset()
				fastEMA = self.emaFast.getWithOffset()
			except Exception as e:
				logging.info(f'EMA get value exception: {e}')
				return 9

			if slowEMA < fastEMA:
				if lastStatus != 1:
					lastStatus = 1
					self.logAndNotif(f"BUY - Price: {lastPrice} (slow {slowEMA} < {fastEMA} fast)")

			elif slowEMA > fastEMA:
				if lastStatus != 2:
					lastStatus = 2
					self.logAndNotif(f"SELL - Price: {lastPrice} (slow {slowEMA} > {fastEMA} fast)")

			else:
				self.logAndNotif(f"HOLD - Price: {lastPrice} (slow {slowEMA} = {fastEMA} fast)")

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

	signal(SIGILL , sigHandler)
	signal(SIGTRAP, sigHandler)
	signal(SIGINT , sigHandler)
	signal(SIGHUP , sigHandler)
	signal(SIGTERM, sigHandler)
	signal(SIGSEGV, sigHandler)

	logging.basicConfig(handlers = [ RotatingFileHandler(log_file, maxBytes = int(argv[10]), backupCount = int(argv[11])) ],
	                    level    = logging.INFO,
	                    format   = '%(asctime)s - %(levelname)s - %(message)s',
	                    datefmt  = '%Y%m%d%H%M%S')

	'''
 	except IOError:
 		sys.stderr.write(f"Creating log file failed: {e.errno} - {e.strerror}\n")
 		sys.exit(1)

 	try:
 		CMD_PIPE_FILE = open(CMD_PIPE_FILE_PATH, "r")

 	except IOError:
 		sys.stderr.write(f"Opeing cmd pipe file failed: {e.errno} - {e.strerror}\n")
  		sys.exit(1)

 	ret = runBot(logFile, BINANCE_PAIR, binance_apiKey, binance_sekKey)
	'''

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

	except Expcepton as e:
		endBot(1, f"BOT Exeption: initialization error: {e}")

	try:
		ret = bot1.connectBinance()
		if ret != 0:
			endBot(ret, f"BOT connect Biance status return ERROR: [{ret}]")

		ret = bot1.walletStatus()
		if ret != 0:
			endBot(ret, f"BOT wallet status return ERROR: [{ret}]")

		ret = bot1.loadData()
		if ret != 0:
			endBot(ret, f"BOT load data return ERROR: [{ret}]")

		ret = bot1.start()
		if ret != 0:
			endBot(ret, f"BOT start return ERROR: [{ret}]")

	except Exception as e:
		endBot(ret, f"BOT EXCEPTION! Exit: {e}")

#	CMD_PIPE_FILE.close()
	endBot(ret, f"BOT return: [{ret}]")

def endBot(code : int, msg : str):
	global pid_file_path

	logging.info(msg)
	logging.shutdown()
	removePidFile()
	exit(code)

if __name__ == '__main__':

	if len(argv) != 14:
		print(f"Usage:\n\t{argv[0]} <WORK_PATH> <BOT_ID> <BINANCE_PAIR> <FAST_EMA> <OFFSET_FAST_EMA> <SLOW_EMA> <OFFSET_SLOW_EMA> <TIME_SAMPLE> <NOTIFY> <MAX_BYE_LOG_SIZE> <LOG_N_ROTATION> <RETRY_TIMEOUT> <MAX_TIMEOUT_TO_EXIT>\nSample:\n\t{argv[0]} ./ BOT1 BTCUSDT 9 0 21 +4 30m twitter 1000000 2 10 100\n\n")
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
		exit(1)

	else:
		main(argv)
