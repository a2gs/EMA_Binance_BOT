#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Andre Augusto Giannotti Scota
# andre.scota@gmail.com
# MIT license

import tweepy
import time
from time import strftime, gmtime

class ntfTwitter:
	ConsAPIKey = str()
	ConsAPIKeySek = str()
	AccssTkn = str()
	AccssTknSek = str()
	twttcli = object()
	twttAuth = object()

	def __init__(self):
		self.ConsAPIKey = str()
		self.ConsAPIKeySek = str()
		self.AccssTkn = str()
		self.AccssTknSek = str()
		self.twttcli = object()
		self.twttAuth = object()

	def auth(self, consapikey, consapikeysek, accsstkn, accsstknsek):
		self.ConsAPIKey = consapikey
		self.ConsAPIKeySek = consapikeysek
		self.AccssTkn = accsstkn
		self.AccssTknSek = accsstknsek

		self.twttAuth = tweepy.OAuthHandler(self.ConsAPIKey, self.ConsAPIKeySek)
		self.twttAuth.set_access_token(self.AccssTkn, self.AccssTknSek)

		self.twttcli = tweepy.API(self.twttAuth)

		try:
			self.twttcli.verify_credentials()
			return -1
		except:
			return 0

	def write(self, idProc, message):
		self.twttcli.update_status(strftime("%Y-%m-%d %H:%M:%S ", gmtime()) + idProc + " " + message)

def logAuth():
	pass

def logWrite():
	pass

def displayAuth():
	pass

def displayWrite():
	pass

class notify:
#	auth = 0
#	write = 0
	twtt = object()

	def __init__(self, typeNtf):
		if typeNtf.lower() == 'twitter':
			self.twtt = ntfTwitter

#			self.auth = self.twtt.auth
#			self.write = self.twtt.write

		elif typeNtf.lower() == 'log':
#			self.auth = logAuth
#			self.write = logWrite
			pass

		elif typeNtf.lower() == 'display':
#			self.auth = displayAuth
#			self.write = displayWrite
			pass

		else:
			pass
