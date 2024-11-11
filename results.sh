#!/bin/sh

BASEDIR=$(dirname "$0")
BASEDIR=$BASEDIR/.Skyfall.app/Contents/Resources
/usr/bin/sqlite3 $BASEDIR/leaderboard.db < $BASEDIR/results.sql > $HOME/Desktop/skyfall-results.txt
