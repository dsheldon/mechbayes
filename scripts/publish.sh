#!/bin/bash

ROOT=$1
SUBDIR=$2
DST=${3:-/var/www/html/covid/}

if [[ $# -lt 2 ]] ; then
    echo 'Two arguments required: root directory and subdirectory relative to root'
    exit 1
fi

ssh doppler mkdir -p $DST
rsync -avz --relative --exclude="*samples*" $ROOT/./$SUBDIR/ doppler:$DST/
