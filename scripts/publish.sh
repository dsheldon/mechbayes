#!/bin/bash

ROOT=$1
SUBDIR=$2
HOST=${3:-doppler}
DST=${4:-/var/www/html/covid}

if [[ $# -lt 2 ]] ; then
    echo 'Two arguments required: root directory and subdirectory relative to root'
    exit 1
fi

ssh $HOST mkdir -p $DST
rsync -avz --relative --exclude="*samples*" $ROOT/./$SUBDIR/ $HOST:$DST/
