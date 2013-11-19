#! /usr/bin/env bash
ORIGINAL_IFS=$IFS
IFS=$'\n'
ffmpeg  -i $1 -v 0  -vf "transpose=$2"  -qscale 0 -y tmp.mov && mv tmp.mov $1
IFS=$ORIGINAL_IFS