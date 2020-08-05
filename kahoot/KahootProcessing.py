#!py -3
from PIL import Image
import os.path
import sys
import random
import csv
from xlsxwriter.workbook import Workbook
# pdf to image: PS C:\Users\jni\Pictures> pdftocairo -jpeg jile.pdf
# (double) with pinyin: py -3 C:\Users\jni\docs\Documents\education\kahoot_processing.py crop .  334 240 970 594
# (triple) with pinyin: py -3 C:\Users\jni\docs\Documents\education\kahoot_processing.py crop .  146 240 1357 594
# pip install Pillow pip install XlsxWriter pip install py-translate pip install pinyin
# https://stackoverflow.com/questions/50854235/how-to-draw-chinese-text-on-the-image-using-cv2-puttextcorrectly-pythonopen
# https://stackoverflow.com/questions/37191008/load-truetype-font-to-opencv/46558093#46558093
# https://haptik.ai/tech/putting-text-on-image-using-python/

# default generate: py -3 C:\Users\jni\docs\Documents\education\kahoot_processing.py generate kahoo.csv C:\Users\jni\docs\Documents\education\kahoot.txt
# py -3 .\kahoot_processing.py generate eggs.csv kahoot.txt 15 3 20 1
# py -3 C:\Users\jni\docs\Documents\education\kahoot_processing.py crop . 337 362 966 477
#  py -3 C:\Users\jni\docs\Documents\education\kahoot_processing.py crop . 586 365 477 477
# kahoot.txt:
# Recognize the character(s).
# Full|Prepare|Dish; Vegetable|Restaurant|Physical exercise|Tea|Fry|Measure word for meal|Fat|A kind of place|Delicious|Variety|Chicken|Reduce|Lose weight|Egg|Then|Extremely|Empty|US dollar|Capable|Beside|Green|Green vegetable|Meat|Soup|Taste|Fresh|Be a guest


COLUMNS = ['', 'Question - max 120 characters', 'Answer 1 - max 75 characters', 'Answer 2 - max 75 characters', 'Answer 3 - max 75 characters',
           'Answer 4 - max 75 characters', "Time limit (sec) – 5, 10, 20, 30, 60, 90, 120, or 240 secs", 'Correct answer(s) - choose at least one']
# QUESTIONS = ['Recognize the character(s).'] * 200
# ALL_CHOICES = ['Full', 'Prepare', 'Dish; Vegetable', 'Restaurant', 'Physical exercise', 'Tea', 'Fry', 'Measure word for meal', 'Fat', 'A kind of place', 'Delicious', 'Variety',
#                'Chicken', 'Reduce', 'Lose weight', 'Egg', 'Then', 'Extremely', 'Empty', 'US dollar', 'Capable', 'Beside', 'Green', 'Green vegetable', 'Meat', 'Soup', 'Taste', 'Fresh', 'Be a guest']
# 1165 504 py -3 C:\Users\jni\docs\Documents\education\kahoot_processing.py crop .  1165 504 1175 955
# 1175 955
# 670 470 py -3 C:\Users\jni\docs\Documents\education\kahoot_processing.py crop .  670 470 1979 1179
# 1979 1179

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

    def crop(self, path='', left=0, right=0, length=0, width=0, output=''):
        #  281 175 226 226
        if not path:
            print("no input or output path specified")
            return
        if left == 0 and right == 0 and length == 0 and width == 0:
            print("no cropping options specified")
            return
        left, right, length, width = int(left), int(
            right), int(length), int(width)
        dirs = os.listdir(path)
        for item in dirs:
            fullpath = os.path.join(path, item)  # corrected
            if os.path.isfile(fullpath):
                f, e = os.path.splitext(fullpath)
                if e not in ['.jpg']:
                    continue
                outputfile = f + '_cropped.jpg' if not output else output
                # print(outputfile)
                try:
                    with Image.open(fullpath) as im:
                        transposed  = im.transpose(Image.ROTATE_90)
                        imCrop = transposed.crop(
                            (left, right, left + length, right + width))  # corrected
                        imCrop.save(outputfile)
                except Exception as inst:
                    print(f"cannot crop {fullpath}:\n{inst}")


def main(argv):
    command = argv.pop(0)
    print(command)
    print(argv)
    processing = KahootProcessing()
    if command == 'crop':
        processing.crop(*argv)
    else:
        processing.create_question_spreadsheet(*argv)


# >>> img = Image.new('RGB', (200, 300), color = (73, 109, 137))
# >>> d = ImageDraw.Draw(img)
# >>> font = ImageFont.truetype('arial.ttf')
# >>> text((100,100), '我', "white", font=font)
# Traceback (most recent call last):
#   File "<stdin>", line 1, in <module>
# TypeError: 'str' object is not callable
# >>> d.text((100,100), '我', "white", font=font)
# >>> img.save('pil_text.png')
# >>> font = ImageFont.truetype('arial.ttf', 100)
# >>> d.text((100,100), '我', "white", font=font)
# >>> img.save('pil_text.png')
# >>> font = ImageFont.truetype('simsun.ttc', 100)

if __name__ == '__main__':
    print(sys.argv)
    main(sys.argv[1:])
