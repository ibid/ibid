#!/bin/sh
# Note that the last comma must be manually removed
echo "["
gunzip -c /usr/share/doc/RFC/links/rfc2821.txt.gz | tail -n +2500 | head -n 50 | egrep '^ *[0-9]{3} ' | sed 's/ *(.*//;s/ *\([0-9]*\) \(.*\)/[["smtp \1"],["\2"]],/'
echo "]"
