MANPAGES=$(patsubst %.md,%,$(wildcard *.md))

all: $(MANPAGES)

clean:
	rm -f $(MANPAGES)

%: %.md
# Incorrect escaping in code blocks:
# http://code.google.com/p/pandoc/issues/detail?id=223
	pandoc -s -t man $< | sed -e '/^[^.]/ s/\\"/"/g' > $@

.PHONY: all clean
