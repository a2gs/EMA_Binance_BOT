#!/usr/bin/env bash

# ------------------------------------------------------------
# Binance Token
export BINANCE_APIKEY=''
export BINANCE_SEKKEY=''

# ------------------------------------------------------------
# Twitter token

# Consumer API keys
export TWITTER_APIKEY=''
export TWITTER_APISEKKEY=''

# Access token & access token secret
export TWITTER_ACCSSTKN=''
export TWITTER_ACCSSSEKTKN=''

# ------------------------------------------------------------

function kbot(){
	kill `head -n 1 $1_pid.text`
}
