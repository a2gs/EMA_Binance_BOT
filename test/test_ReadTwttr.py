#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Andre Augusto Giannotti Scota (https://sites.google.com/view/a2gs/)

import tweepy
from os import getenv

auth = tweepy.OAuthHandler(getenv('TWITTER_APIKEY', 'NOTDEF'), getenv('TWITTER_APISEKKEY', 'NOTDEF'))
auth.set_access_token(getenv('TWITTER_ACCSSTKN', 'NOTDEF'), getenv('TWITTER_ACCSSSEKTKN', 'NOTDEF'))

api = tweepy.API(auth)

print("----------------")

user = api.get_user('A2gsD')
print(f"Screen name: {user.screen_name}")
print(f"Name: {user.name}")
print(f"Description: {user.description}")
print(f"Location: {user.location}")
print(f"Followers count: {user.followers_count}")
for friend in user.followers():
	print(f"Followers name: {friend.screen_name}")

print("---USER-------------")
for tweet in tweepy.Cursor(api.user_timeline).items():
	print(f"{tweet.id}   {tweet.user.name}     {tweet.text}")

print("---MENTIONS-------------")
for tweet in tweepy.Cursor(api.mentions_timeline).items():
	print(f"Id: [{tweet.id}] From: [{tweet.user.name} ({tweet.user.screen_name})] Msg: [{tweet.text}]")

'''
print("---LIST-------------")
for tweet in tweepy.Cursor(api.list_timeline).items():
	print(f"{tweet.id}   {tweet.user.name}     {tweet.text}")

print("---HOME-------------")
for tweet in tweepy.Cursor(api.home_timeline).items():
	print(f"{tweet.id}   {tweet.user.name}     {tweet.text}")
'''

#API.get_direct_message
#API.send_direct_message
#api.destroy_status(1266582771436343296)
