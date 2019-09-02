#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Andre Augusto Giannotti Scota
# andre.scota@gmail.com
# MIT license

import os
import sys
import atexit
import time

from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceWithdrawException, BinanceRequestException

PID_NUM       = 0
PID_FILE      = ''
CMD_PIPE_FILE = ''
LOG_FILE      = ''
WORK_PATH     = ''
BINANCE_PAIR  = ''

def removePidFile():
	global PID_FILE

	os.remove(PID_FILE)

def daemonize():
	global PID_FILE
	global PID_NUM
	global WORK_PATH

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

	f = open(PID_FILE, 'w+')
	f.write(f"{PID_NUM}\n{CMD_PIPE_FILE}\n{LOG_FILE}\n{WORK_PATH}\n{BINANCE_PAIR}\n")
	f.close()

def runBot():
	binance_apiKey = os.getenv('BINANCE_APIKEY', 'NOTDEF_APIKEY')
	binance_sekKey = os.getenv('BINANCE_SEKKEY', 'NOTDEF_SEKKEY')
	logFile = open(LOG_FILE, 'a')

	logFile.write(f"\n==================================================================\nConfiguration:\n")
	logFile.write(f"\tPID = [{PID_NUM}]\n")
	logFile.write(f"\tPID file = [{PID_FILE}]\n")
	logFile.write(f"\tCMD pipe = [{CMD_PIPE_FILE}]\n")
	logFile.write(f"\tWorking path = [{WORK_PATH}]\n")
	logFile.write(f"\tBinance pair = [{BINANCE_PAIR}]\n")
	logFile.write(f"\tBinance API key = [{binance_apiKey}]\n\n")

	logFile.write(f"--- Stating ---\n")

	client = Client(binance_apiKey, binance_sekKey, {"verify": True, "timeout": 20})

	try:
		getPrice = client.get_symbol_ticker(symbol=BINANCE_PAIR)

	except BinanceAPIException as e:
		logFile.write(f'Binance API exception: {e.status_code} - {e.message}\n')
		logFile.close()
		return 1

	except BinanceRequestException as e:
		logFile.write(f'Binance request exception: {e.status_code} - {e.message}\n')
		logFile.close()
		return 2

	except BinanceWithdrawException as e:
		logFile.write(f'Binance withdraw exception: {e.status_code} - {e.message}\n')
		logFile.close()
		return 3

	logFile.write(f'Symbol: [' + getPrice['symbol'] + ']\n')
	logFile.write(f'Price.: [' + getPrice['price'] + ']\n')

	logFile.close()
	return 0

def main(argv):
	ret = 0

	global PID_FILE
	global CMD_PIPE_FILE
	global LOG_FILE
	global WORK_PATH
	global BINANCE_PAIR

	WORK_PATH     = argv[1]
	PID_FILE      = f"{argv[2]}_pid.text"
	CMD_PIPE_FILE = f"{argv[2]}_pipecmd.text"
	LOG_FILE      = f"{argv[2]}_log.text"
	BINANCE_PAIR  = argv[3]

	daemonize()

	ret = runBot()

	sys.exit(ret)

if __name__ == '__main__':

	if len(sys.argv) != 4:
		print(f"Usage:\n\t{sys.argv[0]} <BOT_ID> <WORK_PATH> <BINANCE_PAIR>\nSample:\n\t{sys.argv[0]} ./ BOT1 BNBBTC\n")
		sys.exit(1)

	else:
		main(sys.argv)
