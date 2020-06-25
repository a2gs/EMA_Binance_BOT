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
	'1m'  : [Client.KLINE_INTERVAL_1MINUTE, 60],
	'3m'  : [Client.KLINE_INTERVAL_3MINUTE, 180],
	'5m'  : [Client.KLINE_INTERVAL_5MINUTE, 300],
	'15m' : [Client.KLINE_INTERVAL_15MINUTE, 900],
	'30m' : [Client.KLINE_INTERVAL_30MINUTE, 1800],
	'1h'  : [Client.KLINE_INTERVAL_1HOUR, 3600],
	'2h'  : [Client.KLINE_INTERVAL_2HOUR, 7200],
	'4h'  : [Client.KLINE_INTERVAL_4HOUR, 14400],
	'6h'  : [Client.KLINE_INTERVAL_6HOUR, 21600],
	'8h'  : [Client.KLINE_INTERVAL_8HOUR, 28800],
	'12h' : [Client.KLINE_INTERVAL_12HOUR, 43200],
	'1d'  : [Client.KLINE_INTERVAL_1DAY, 86400],
	'3d'  : [Client.KLINE_INTERVAL_3DAY, 259200],
	'1w'  : [Client.KLINE_INTERVAL_1WEEK, 604800],
	'1M'  : [Client.KLINE_INTERVAL_1MONTH, 2629746]
}
