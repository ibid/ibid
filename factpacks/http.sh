#!/bin/sh
# Note that the last comma must be manually removed
echo "["
zgrep -E '^10\.[0-9]+\.[0-9]+' /usr/share/doc/RFC/links/rfc2068.txt.gz | sed 's/^[^ ]* /[["http/; s/ /"], ["is /; s/$/"]],/; s/http/http /'
echo "]"
