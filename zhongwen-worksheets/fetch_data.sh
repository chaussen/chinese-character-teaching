#!/usr/bin/env bash
# One-time: download the open stroke/radical dataset used for enrichment.
# makemeahanzi is CC BY 4.0 — credit it in anything you publish.
set -e
mkdir -p vendor
curl -L -o vendor/dictionary.txt https://raw.githubusercontent.com/skishore/makemeahanzi/master/dictionary.txt
curl -L -o vendor/graphics.txt   https://raw.githubusercontent.com/skishore/makemeahanzi/master/graphics.txt
echo "vendor/ ready ($(du -sh vendor | cut -f1))"
