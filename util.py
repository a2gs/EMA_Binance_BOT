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
import signal
import logging

def cleanUp(pid_file_path, cmd_pipe_file_path):
	os.remove(pid_file_path)
	os.remove(cmd_pipe_file_path)

def sigHandler(signum, frame):
	sys.stderr.write(f'Singal {signum} received\n')
	logging.info(f'Singal {signum} received\n')
	logging.shutdown()
	sys.exit(0)

auxPid_file_path = ''
auxCmd_pipe_file_path = ''

def removePidFile():
	global auxPid_file_path
	global auxCmd_pipe_file_path

	cleanUp(auxPid_file_path, auxCmd_pipe_file_path)

def daemonize(work_path):
	pid_num = 0

	try:
		pid_num = os.fork()
		if pid_num > 0:
			sys.exit(0)

	except OSError as e:
		sys.stderr.write(f"Fork failed: {e.errno} - {e.strerror}\n")
		sys.exit(1)

	os.chdir(work_path)
	os.setsid()
	os.umask(0)

#	atexit.register(removePidFile)

	return(os.getpid())
