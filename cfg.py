#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Andre Augusto Giannotti Scota
# andre.scota@gmail.com
# MIT license

from binance.client import Client

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
