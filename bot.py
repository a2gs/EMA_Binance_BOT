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

from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceWithdrawException, BinanceRequestException

PID_NUM            = 0
PID_FILE_PATH      = ''
CMD_PIPE_FILE      = ''
CMD_PIPE_FILE_PATH = ''
LOG_FILE           = ''
WORK_PATH          = ''
BINANCE_PAIR       = ''

# ----------------------------------------------------------------------------------------

def removePidFile():
	global PID_FILE_PATH
	global CMD_PIPE_FILE_PATH

	os.remove(PID_FILE_PATH)
	os.remove(CMD_PIPE_FILE_PATH)

def daemonize():
	global PID_FILE_PATH
	global PID_NUM
	global WORK_PATH
	global BINANCE_PAIR

	try:
		PID_NUM = os.fork()
		if PID_NUM > 0:
			sys.exit(0)

	except OSError as e:
		sys.stderr.write(f"Fork failed: {e.errno} - {e.strerror}\n")
		sys.exit(1)

	os.chdir(WORK_PATH)
	os.setsid()
	os.umask(0)

	atexit.register(removePidFile)
	PID_NUM = str(os.getpid())

	f = open(PID_FILE_PATH, 'w+')
	f.write(f"{PID_NUM}\n{CMD_PIPE_FILE_PATH}\n{LOG_FILE}\n{WORK_PATH}\n{BINANCE_PAIR}\n")
	f.close()

# ----------------------------------------------------------------------------------------

def runBot(log, binancePair, apikey, sekkey):
	log.write(time.strftime("%d/%m/%Y %H:%M:%S", time.localtime()) + " --- Stating ---\n")

	client = Client(apikey, sekkey, {"verify": True, "timeout": 20})

	try:
		getPrice = client.get_symbol_ticker(symbol=binancePair)

	except BinanceAPIException as e:
		log.write(time.strftime("%d/%m/%Y %H:%M:%S ", time.localtime()) + f'Binance API exception: {e.status_code} - {e.message}\n')
		return 1

	except BinanceRequestException as e:
		log.write(time.strftime("%d/%m/%Y %H:%M:%S ", time.localtime()) + f'Binance request exception: {e.status_code} - {e.message}\n')
		return 2

	except BinanceWithdrawException as e:
		log.write(time.strftime("%d/%m/%Y %H:%M:%S ", time.localtime()) + f'Binance withdraw exception: {e.status_code} - {e.message}\n')
		return 3

	log.write(time.strftime("%d/%m/%Y %H:%M:%S ", time.localtime()) + f'Symbol: [' + getPrice['symbol'] + '] Price: [' + getPrice['price'] + ']\n')

	return 0

# ----------------------------------------------------------------------------------------

def main(argv):
	ret = 0

	binance_apiKey = os.getenv('BINANCE_APIKEY', 'NOTDEF_APIKEY')
	binance_sekKey = os.getenv('BINANCE_SEKKEY', 'NOTDEF_SEKKEY')

	global PID_FILE_PATH
	global CMD_PIPE_FILE
	global CMD_PIPE_FILE_PATH
	global LOG_FILE
	global WORK_PATH
	global BINANCE_PAIR

	WORK_PATH          = argv[1]
	PID_FILE_PATH      = f"{argv[2]}_pid.text"
	CMD_PIPE_FILE_PATH = f"{argv[2]}_pipecmd"
	LOG_FILE           = f"{argv[2]}_log.text"
	BINANCE_PAIR       = argv[3]

	daemonize()

	logFile = open(LOG_FILE, 'a')

	logFile.write(f"\n================================================================\nConfiguration:\n")
	logFile.write(f"\tPID = [{PID_NUM}]\n")
	logFile.write(f"\tPID file = [{PID_FILE_PATH}]\n")
	logFile.write(f"\tCMD pipe = [{CMD_PIPE_FILE_PATH}]\n")
	logFile.write(f"\tWorking path = [{WORK_PATH}]\n")
	logFile.write(f"\tBinance pair = [{BINANCE_PAIR}]\n")
	logFile.write(f"\tBinance API key = [{binance_apiKey}]\n\n")

	try:
		os.mkfifo(CMD_PIPE_FILE_PATH)

	except OSError as e: 
		logFile.write(time.strftime("%d/%m/%Y %H:%M:%S ", time.localtime()) + f"Erro creating cmd pipe file: {e.errno} - {e.strerror}\n")
		ret = 1

	else:
		# CMD_PIPE_FILE = open(CMD_PIPE_FILE_PATH, "rw")
		ret = runBot(logFile, BINANCE_PAIR, binance_apiKey, binance_sekKey)

	logFile.close()

	sys.exit(ret)

if __name__ == '__main__':

	if len(sys.argv) != 4:
		print(f"Usage:\n\t{sys.argv[0]} <BOT_ID> <WORK_PATH> <BINANCE_PAIR>\nSample:\n\t{sys.argv[0]} ./ BOT1 BNBBTC\n")
		sys.exit(1)

	else:
		main(sys.argv)
