#!/usr/bin/env python3
from KahootProcessing import KahootProcessing
import pinyin
print(pinyin.get("从来"))
processing = KahootProcessing()
# processing.create_question_spreadsheet('kahoot.csv','kahoot.txt')
processing.translate_pinyin_question_spreadsheet('kahoot.csv','kahoot.txt',reverse=True)
# processing.convert_to_xlsx('kahoot.csv')
