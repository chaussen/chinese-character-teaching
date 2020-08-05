#!/usr/bin/env python3
from configs import COLUMNS, CHARACTER_PINYIN_MAPPING, PinyinToneMark
import random
import csv
from xlsxwriter.workbook import Workbook
# from xpinyin import Pinyin
import pinyin.cedict
import pinyin
# >>> pinyin.cedict.translate_word('你')
# ['you (informal, as opposed to courteous 您[nin2])']
# >>> pinyin.cedict.translate_word('你好')


class KahootProcessing:
    def __init__(self):
        pass

    def read_question_configs(self, config_file):
        lines = []
        with open(config_file, 'rt', encoding="utf8") as file:
            for line in file:
                line = line.strip()  # or some other preprocessing
                lines.append(line)  # storing everything in memory!
        return lines

    def write_csv(self, csvfile, answers, question):
        # answers = self.generate_random_choices()
        print(csvfile)
        with open(csvfile, 'w', newline='', encoding="utf8") as csvfile:
            spamwriter = csv.writer(csvfile)
            spamwriter.writerow(COLUMNS)
            count = len(answers)
            for i in range(count):
                answer_line = answers[i]
                spamwriter.writerow(
                    [str(i), question] + answer_line)
                # [str(i), QUESTIONS[i]] + answer_line)

    def convert_to_xlsx(self, csvfile):
        workbook = Workbook(csvfile[:-4] + '.xlsx')
        worksheet = workbook.add_worksheet()
        with open(csvfile, 'rt', encoding="utf8") as f:
            reader = csv.reader(f)
            for r, row in enumerate(reader):
                for c, col in enumerate(row):
                    worksheet.write(r, c, col)
        print(csvfile[:-4] + '.xlsx')
        workbook.close()

    def generate_random_choices(self, answers, count=2, number=3, timeout=20, correct_choice=1):
        results = []
        question_list = random.sample(answers, count)
        # question_list = random.sample(ALL_CHOICES, count)
        for answer in question_list:
            answers.remove(answer)
            # print(f"reduced answers: {answers}")
            answer_line = random.sample(answers, number)
            # print(f'answer_line without correct answer is: {answer_line}')
            answer_line.insert(0, answer)
            answer_line.append(timeout)
            answer_line.append(correct_choice)
            results.append(answer_line[:])
            answers.append(answer)
            # print(f"recovered answers: {answers}")
        return results

    def create_question_spreadsheet(self, csvfile, config_file, count=0, number=3, timeout=20, correct_choice=1):
        count = int(count)
        number = int(number)
        configs = self.read_question_configs(config_file)
        question = configs[0]
        answers = configs[1].split('|')
        # print(answers)
        question_count = len(answers)
        print(f"there are {question_count} answers: {answers}")
        if count == 0:
            count = question_count
        lines = self.generate_random_choices(answers,
                                             count, number, timeout, correct_choice)
        self.write_csv(csvfile, lines, question)
        self.convert_to_xlsx(csvfile)

    def write_question_and_answers_csv(self, csvfile, answers, questions):
        # answers = self.generate_random_choices()
        print(csvfile)
        with open(csvfile, 'w', newline='', encoding="utf8") as csvfile:
            spamwriter = csv.writer(csvfile)
            spamwriter.writerow(COLUMNS)
            count = len(answers)
            for i in range(count):
                answer_line = answers[i]
                spamwriter.writerow(
                    [str(i), questions[i]] + answer_line)

    def decode_pinyin(self, s):
        s = s.lower()
        r = ""
        t = ""
        for c in s:
            if c >= 'a' and c <= 'z':
                t += c
            elif c == ':':
                assert t[-1] == 'u'
                t = t[:-1] + "\u00fc"
            else:
                if c >= '0' and c <= '5':
                    tone = int(c) % 5
                    if tone != 0:
                        m = re.search("[aoeiuv\u00fc]+", t)
                        if m is None:
                            t += c
                        elif len(m.group(0)) == 1:
                            t = t[:m.start(
                                0)] + PinyinToneMark[tone][PinyinToneMark[0].index(m.group(0))] + t[m.end(0):]
                        else:
                            if 'a' in t:
                                t = t.replace("a", PinyinToneMark[tone][0])
                            elif 'o' in t:
                                t = t.replace("o", PinyinToneMark[tone][1])
                            elif 'e' in t:
                                t = t.replace("e", PinyinToneMark[tone][2])
                            elif t.endswith("ui"):
                                t = t.replace("i", PinyinToneMark[tone][3])
                            elif t.endswith("iu"):
                                t = t.replace("u", PinyinToneMark[tone][4])
                            else:
                                t += "!"
                r += t
                t = ""
        r += t
        return r

    def translate_pinyin_question_spreadsheet(self, csvfile, source, english=True, reverse=False):
        # read question template and answers
        configs = self.read_question_configs(source)
        question = configs[0]
        answers = configs[1].split('|')
        question_count = len(answers)
        questions = [question] * question_count
        actual_answers = answers
        question_answer = {}
        # check if pinyin is provided. if not use default
        for i, answer in enumerate(answers):
            current_pinyin = CHARACTER_PINYIN_MAPPING.get(answer, '')
            if current_pinyin:
                pinyins = []
                for p in current_pinyin.split(' '):
                    r = self.decode_pinyin(p)
                    pinyins.append(r)
                current_pinyin = ''.join(pinyins)
            else:
                current_pinyin = pinyin.get(answer)
            # construct question with corresponding pinyin

            if english:
                # get the first meaning of the word
                meanings = pinyin.cedict.translate_word(answer)
                answer = meanings[0]
                actual_answers[i] = answer
            if reverse:
                answer, current_pinyin = current_pinyin, answer
                actual_answers[i] = answer

            print(f'''"{answer}": "{current_pinyin}",''')
            current_question = question.replace('{answer}', current_pinyin)
            if reverse:
                current_question = current_question.replace('meaning', 'sound')
            questions[i] = current_question
            question_answer[actual_answers[i]] = questions[i]

        lines = self.generate_random_choices(actual_answers,
                                             question_count, 3, 20, 1)
        for j, line in enumerate(lines):
            questions[j] = question_answer[line[0]]
        self.write_question_and_answers_csv(csvfile, lines, questions)
        self.convert_to_xlsx(csvfile)
