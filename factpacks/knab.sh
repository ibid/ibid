#!/bin/sh -e
KNABDIR="$1"
./knab.py "$KNABDIR/handey.knb" "jack handey" "be jack handey" > handey.json
./knab.py "$KNABDIR/zippy.knb" "be zippy" "be ed" > zippy.json
./knab.py "$KNABDIR/overlord.knb" "overlord" > overlord.json
./knab.py "$KNABDIR/wrestling.knb" "wrestling moves" > wrestling.json
./knab.py "$KNABDIR/tao.knb" "tao" > tao.json
./knab.py "$KNABDIR/rubaiyat.knb" "rubaiyat" > rubaiyat.json
