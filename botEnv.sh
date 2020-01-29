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

	pidfile="$1"_pid.text

	botpid=`head -n 1 $pidfile`
	kill "$botpid"

	sleep 1

	if [ -f "$pidfile" ]; then

		botpid=`head -n 1 $pidfile`

		if [ ! -z "$botpid" ]; then
			kill -9 "$botpid"
		fi

	fi
}
