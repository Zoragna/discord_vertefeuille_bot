#!/bin/sh

. /etc/credentials/.secret.txt
export $(cut -d= -f1 /etc/credentials/.secret.txt)

printenv
