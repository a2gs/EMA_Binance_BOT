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

class botCfg:
	cfg = {}

	def get(self, param):
		return self.cfg.get(param, 'UNDEF')

	def set(self, param, value):
		self.cfg[param] = value

cfg = botCfg()

# ----------------------------------------------------------------------------------------

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

def runBot(log):
	global cfg

	pair = cfg.get('binance_pair')

	log.write(time.strftime("%d/%m/%Y %H:%M:%S", time.localtime()) + " --- Stating ---\n")

	client = Client(cfg.get('binance_apikey'), cfg.get('binance_sekkey'), {"verify": True, "timeout": 20})

	# Exchange status
	if client.get_system_status()['status'] != 0:
		print('Binance out of service')
		return 1

	# 1 Pair wallet
	pair1 = client.get_asset_balance(pair[:3])
	log.write(time.strftime("%d/%m/%Y %H:%M:%S ", time.localtime()) + f'Symbol 1 on wallet: [' + pair[:3] + ']\tFree: [' + pair1['free'] + ']\tLocked: [' + pair1['locked'] + ']\n')

	# 2 Pair wallet
	pair2 = client.get_asset_balance(pair[3:])
	log.write(time.strftime("%d/%m/%Y %H:%M:%S ", time.localtime()) + f'Symbol 2 on wallet: [' + pair[3:] + ']\tFree: [' + pair2['free'] + ']\tLocked: [' + pair2['locked'] + ']\n')

	# Open orders
	openOrders = client.get_open_orders(symbol=pair)
	for openOrder in openOrders:
		log.write(time.strftime("%d/%m/%Y %H:%M:%S ", time.localtime()) + f'Order id [' + str(openOrder['orderId']) + '] data:\n' 
							 + '\tPrice.......: [' + openOrder['price']          + ']\n'
							 + '\tQtd.........: [' + openOrder['origQty']        + ']\n'
							 + '\tQtd executed: [' + openOrder['executedQty']    + ']\n'
							 + '\tSide........: [' + openOrder['side']           + ']\n'
							 + '\tType........: [' + openOrder['type']           + ']\n'
							 + '\tStop price..: [' + openOrder['stopPrice']      + ']\n'
							 + '\tIs working..: [' + str(openOrder['isWorking']) + ']\n')


	# Pair price
	try:
		getPrice = client.get_symbol_ticker(symbol=cfg.get('binance_pair'))

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

	global cfg

	cfg.set('binance_apikey', os.getenv('BINANCE_APIKEY', 'NOTDEF_APIKEY'))
	cfg.set('binance_sekkey', os.getenv('BINANCE_SEKKEY', 'NOTDEF_APIKEY'))

	cfg.set('work_path', argv[1])
	cfg.set('pid_file_path', f"{argv[2]}_pid.text")
	cfg.set('cmd_pipe_file_path', f"{argv[2]}_pipecmd")
	cfg.set('log_file', f"{argv[2]}_log.text")
	cfg.set('binance_pair', argv[3])
	cfg.set('fast_ema', argv[4])
	cfg.set('slow_ema', argv[5])
	cfg.set('time_sample', argv[6])

	daemonize()

	try:
		logFile = open(cfg.get('log_file'), 'a')

	except IOError:
		sys.stderr.write(f"Creating log file failed: {e.errno} - {e.strerror}\n")
		sys.exit(1)

	logFile.write(f"\n================================================================\nConfiguration:\n")
	logFile.write(f"\tPID = [{cfg.get('pid')}]\n")
	logFile.write(f"\tPID file = [{cfg.get('pid_file_path')}]\n")
	logFile.write(f"\tCMD pipe = [{cfg.get('cmd_pipe_file_path')}]\n")
	logFile.write(f"\tWorking path = [{cfg.get('work_path')}]\n")
	logFile.write(f"\tBinance pair = [{cfg.get('binance_pair')}]\n")
	logFile.write(f"\tEMA Slow/Fast = [{cfg.get('slow.ema')} / {cfg.get('fast_ema')}]\n")
	logFile.write(f"\tTime sample = [{cfg.get('time_sample')}]\n")
	logFile.write(f"\tBinance API key = [{cfg.get('binance_apikey')}]\n\n")

	try:
		os.mkfifo(cfg.get('cmd_pipe_file_path'))

	except OSError as e: 
		logFile.write(time.strftime("%d/%m/%Y %H:%M:%S ", time.localtime()) + f"Erro creating cmd pipe file: {e.errno} - {e.strerror}\n")
		sys.exit(1)

#	try:
#		CMD_PIPE_FILE = open(CMD_PIPE_FILE_PATH, "r")

#	except IOError:
#		sys.stderr.write(f"Opeing cmd pipe file failed: {e.errno} - {e.strerror}\n")
# 		sys.exit(1)

#	ret = runBot(logFile, BINANCE_PAIR, binance_apiKey, binance_sekKey)
	ret = runBot(logFile)

	logFile.write(time.strftime("%d/%m/%Y %H:%M:%S ", time.localtime()) + f"BOT return: [{ret}]\n")

#	CMD_PIPE_FILE.close()
	logFile.close()

	sys.exit(ret)

if __name__ == '__main__':

	if len(sys.argv) != 7:
		print(f"Usage:\n\t{sys.argv[0]} <BOT_ID> <WORK_PATH> <BINANCE_PAIR> <FAST_EMA> <SLOW_EMA> <TIME_SAMPLE>\nSample:\n\t{sys.argv[0]} ./ BOT1 BNBBTC\n")
		sys.exit(1)

	else:
		main(sys.argv)
