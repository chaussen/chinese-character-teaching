#!/usr/bin/env python3
from kahoot_processor import KahootProcessing
import pinyin
# processing.create_question_spreadsheet('kahoot.csv','kahoot.txt')
# print(pinyin.get("从来"))
print("Start...")
processing = KahootProcessing()
# processing.translate_pinyin_question_spreadsheet('kahoot1.csv', 'kahoot.txt',english=True, reverse=False)
# processing.translate_pinyin_question_spreadsheet('kahoot2.csv', 'kahoot.txt',english=False, reverse=True)
# processing.translate_pinyin_question_spreadsheet('kahoot3.csv', 'kahoot.txt',english=False, reverse=False)
# processing.translate_pinyin_question_spreadsheet('kahoot4.csv', 'kahoot.txt',english=True, reverse=True)
# processing.generate_mixed_questions(71, 'kahoot.csv',
#                                     ['kahoot1.csv',
#                                      'kahoot2.csv', 'kahoot3.csv',
#                                      'kahoot4.csv'])
processing.convert_to_xlsx('kahoot.csv')
