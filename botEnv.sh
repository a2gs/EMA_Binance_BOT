#!/usr/bin/env bash

export BINANCE_APIKEY=''
export BINANCE_SEKKEY=''

function kbot(){
	kill `head -n 1 $1_pid.text`
}
