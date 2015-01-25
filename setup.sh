#!/bin/sh

if [ -f data/data.sqlite ]; then
	echo "data/data.sqlite already exists. Nothing will be done."
	exit 1
fi

mkdir data
sqlite3 data/data.sqlite < sql/setup.sql
