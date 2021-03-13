#!/usr/bin/env python3
from kahoot_configs import COLUMNS
import random
import csv
from xlsxwriter.workbook import Workbook
import pinyin.cedict
import pinyin
import path_configs
from googletrans import Translator
from character_pinyin_constants import CHARACTER_PINYIN_ENGLISH_MAPPING
from character_pinyin_constants import decode_pinyin


class KahootProcessing:
    def __init__(self):
        pass
        # self.translator = Translator()

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

    def generate_random_choices(self, answers,
                                count=2, number=3,
                                timeout=20, correct_choice=1):
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

    def create_question_spreadsheet(self, csvfile,
                                    config_file, count=0,
                                    number=3, timeout=20, correct_choice=1):
        count = int(count)
        number = int(number)
        configs = self.read_question_configs(config_file)
        question = configs[0]
        answers = configs[1].split('|')
        # print(answers)
        question_count = len(answers)
        # print(f"there are {question_count} answers: {answers}")
        if count == 0:
            count = question_count
        lines = self.generate_random_choices(answers,
                                             count, number,
                                             timeout, correct_choice)
        self.write_csv(csvfile, lines, question)
        # self.convert_to_xlsx(csvfile)

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

    def translate_pinyin_question_spreadsheet(self, csvfile,
                                              source, english=True,
                                              reverse=False):
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
            print(f'''answer: {answer}''')
            current_pinyin_english = CHARACTER_PINYIN_ENGLISH_MAPPING.get(answer, None)
            pinyin_part = ''
            english_part = ''
            current_pinyin = ''
            current_english = ''
            if current_pinyin_english:
                pinyin_part = current_pinyin_english[0]
                english_part = current_pinyin_english[1]
            if pinyin_part:
                pinyins = []
                for p in pinyin_part.split(' '):
                    r = decode_pinyin(p)
                    pinyins.append(r)
                current_pinyin = ''.join(pinyins)
            else:
                current_pinyin = pinyin.get(answer)
            # construct question with corresponding pinyin

            if english:
                meanings = pinyin.cedict.translate_word(answer)
                if english_part:
                    current_english = english_part
                elif meanings:
                    current_english = ';'.join(meanings)
                    if len(current_english) > 75:
                        current_english = current_english[:72] + '...'
                else:
                    current_english = answer + current_pinyin
                actual_answers[i] = current_english
            if reverse:
                if not current_english:
                    current_english = answer
                current_english, current_pinyin = current_pinyin, current_english
                actual_answers[i] = current_english

            # print(f'''"{answer}": "{current_pinyin}",''')
            current_question = question.replace('{answer}', current_pinyin)
            if reverse:
                current_question = current_question.replace(
                    'meaning', 'pinyin')
            questions[i] = current_question
            question_answer[actual_answers[i]] = questions[i]

        lines = self.generate_random_choices(actual_answers,
                                             question_count, 3, 20, 1)
        for j, line in enumerate(lines):
            questions[j] = question_answer[line[0]]
        name = question.split(' ', 1)[0]
        dest = csvfile[:-1] + name + csvfile[-1] + '.csv'
        self.write_question_and_answers_csv(dest, lines, questions)
        return name
        # self.convert_to_xlsx(csvfile)

    def generate_mixed_questions(self, question_count, resultfile, csvfiles):
        count_each = question_count // len(csvfiles)
        question_number = 1
        final_questions = []
        for csvfile in csvfiles:
            lines = []
            with open(csvfile, 'rt', encoding="utf8") as file:
                for line in file:
                    line = line.strip()  # or some other preprocessing
                    lines.append(line)  # storing everything in memory!
            questions = lines[1:]
            question_list = random.sample(questions, count_each)
            final_questions = final_questions + question_list
        random.shuffle(final_questions)
        with open(resultfile, 'w', newline='', encoding="utf8") as csvouput:
            spamwriter = csv.writer(csvouput)
            spamwriter.writerow(COLUMNS)
            for answer_line in final_questions:
                number, content = answer_line.split(',', 1)
                content = content.replace('""', '!').replace('"', '')
                content = content.replace('!', '"')
                newline = [str(question_number)] + content.split(',')
                spamwriter.writerow(newline)
                question_number = question_number + 1
