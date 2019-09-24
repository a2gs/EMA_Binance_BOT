#!/usr/bin/env bash

export BINANCE_APIKEY='372YzaY3nTItd1Z8SE8TZH8vFkdnnJuxAiRCM3KwZq3lmJewL4ta2LO5VgsaSI0Y'
export BINANCE_SEKKEY='XTaSTNiOEbvmCmp5zyFChxkJLQYdb85sRBf8cgP5qCn8JYiEXRpYVsX9Hjt1MRsW'

function kbot(){
	kill `head -n 1 $1_pid.text`
}
