import tkinter as tk
import path_configs
from character_pinyin_constants import decode_pinyin
from character_pinyin_constants import CHARACTER_PINYIN_ENGLISH_MAPPING
from character_card_maker import ChineseCardMaker
from kahoot_processor import KahootProcessing
import subprocess
import urllib.parse
from xpinyin import Pinyin
import pinyin.cedict
from googletrans import Translator


flash_player = "C:\\Users\\abc\\Documents\\jobs\\teaching\\chinese\\zhongwen\\Adobe Flash Player.exe"
flash_card_url = '''http://www.yes-chinese.com/card/cardB.swf?value='''


class Application(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.pack()
        self.card_maker = ChineseCardMaker()
        self.processing = KahootProcessing()
        self.create_widgets()
        # self.translator = Translator()
        self.row = 0
        self.question = ''

    def create_widgets(self):
        self._translate_widget(0)
        self._question_sheet_widget(1)
        self._spreadsheet_widget(2)
        self._separate_image_widget(3)
        self._full_card_widget(4)
        self._flash_stroke_widget(5)
        self._pinyin_widget(6)
        self._quit_widget(7)

    def _translate_widget(self, row):
        v = tk.StringVar(self, value='put in chinese here')
        self.entry = tk.Entry(self, textvariable=v)
        self.entry.grid(row=row, column=0)
        self.translate = tk.Button(self)
        self.translate["text"] = "Translate to English"
        self.translate["command"] = self.translate_to_english
        self.translate.grid(row=row, column=1)

    def _question_sheet_widget(self, row):
        # define button and checkbox
        self.english_var = tk.BooleanVar()
        self.reverse_var = tk.BooleanVar()
        self.english_check = tk.Checkbutton(
            self, text="English", variable=self.english_var)
        self.reverse_check = tk.Checkbutton(
            self, text="Reverse", variable=self.reverse_var)
        self.questions = tk.Button(
            self, text="Kahoot: Generate questions", fg="blue", command=self.create_question_sheet)

        # initialize values
        self.english_var.set(False)
        self.reverse_var.set(False)

        # drawing
        self.english_check.grid(row=row, column=0)
        self.reverse_check.grid(row=row, column=1)
        self.questions.grid(row=row, column=2)

    def _spreadsheet_widget(self, row):
        self.question_count = tk.Entry(self)
        self.question_count.grid(row=row, column=0)
        self.xlsx = tk.Button(self, text="Kahoot: Create XLSX file",
                              fg="green", command=self.create_xlsx)
        self.xlsx.grid(row=row, column=1)

    def _separate_image_widget(self, row):
        self.separate_image = tk.Button(self, text="Create separate images for character and pinyin",
                                        fg="aqua", command=self.generate_separate_images)
        self.separate_image.grid(row=row, column=0)

    def _full_card_widget(self, row):
        self.full_card = tk.Button(self, text="Create card with pinyin and character",
                                   fg="purple", command=self.generate_character_pinyin_image)
        self.full_card.grid(row=row, column=0)

    def _flash_stroke_widget(self, row):
        self.characters = tk.Entry(self)
        self.characters.grid(row=row, column=0)
        self.stroke = tk.Button(self, text="Show stroke order",
                                fg="black", command=self.show_stroke_order)
        self.stroke.grid(row=row, column=1)

    def _pinyin_widget(self, row):
        self.to_pinyin = tk.Entry(self)
        self.to_pinyin.grid(row=row, column=0)
        self.pinyin = tk.Button(self, text="Show pinyin character and english",
                                fg="black", command=self.print_pinyin_translation)
        self.pinyin.grid(row=row, column=1)
        self.mystr = tk.StringVar()
        self.show_pinyin = tk.Entry(self, textvariable=self.mystr,
                                    state='readonly').grid(row=row,
                                                           column=2,
                                                           padx=10,
                                                           pady=10)

    def _quit_widget(self, row):
        self.quit = tk.Button(self, text="QUIT", fg="red",
                              command=self.master.destroy)
        self.quit.grid(row=row, column=0)

    def show_stroke_order(self):
        characters = self.characters.get()
        encoded = urllib.parse.quote(characters)
        url = flash_card_url + encoded
        subprocess.run([flash_player, url])

    def create_question_sheet(self):
        english = self.english_var.get()
        reverse = self.reverse_var.get()
        source = '../kahoot/kahoot.txt'
        destination = ''
        if english is True and reverse is False:
            destination = '../kahoot/1'
        if english is False and reverse is True:
            destination = '../kahoot/2'
        if english is False and reverse is False:
            destination = '../kahoot/3'
        if english is True and reverse is True:
            destination = '../kahoot/4'

        question = self.processing.translate_pinyin_question_spreadsheet(
            destination, source, english=english, reverse=reverse)
        self.question = question

    def generate_separate_images(self):
        self.card_maker.generate_separate_images()

    def translate_to_english(self):
        text = self.entry.get()
        if text:
            self.card_maker.translate_to_english(text)

    def create_xlsx(self):
        whole_csv = f'''../kahoot/{self.question}kahoot.csv'''
        self.processing.generate_mixed_questions(
            int(self.question_count.get()),
            whole_csv,
            [
                f'''../kahoot/{self.question}1.csv''',
                f'''../kahoot/{self.question}2.csv''',
                f'''../kahoot/{self.question}3.csv''',
                f'''../kahoot/{self.question}4.csv'''
            ])
        self.processing.convert_to_xlsx(whole_csv)

# cc.translate_to_english("慈")
    def generate_character_pinyin_image(self):
        self.card_maker.generate_character_pinyin_image()

    def __get_next_row(self):
        return self.row

    def print_pinyin_translation(self):
        characters = self.to_pinyin.get().split('|')
        results_pinyin_english = []
        results_english_pinyin = []
        results_character_english = []
        results_english_character = []
        results_character_pinyin = []
        for character in characters:
            pinyin_english = CHARACTER_PINYIN_ENGLISH_MAPPING.get(
                character, None)
            pinyins = []
            defined_pinyin = ''
            defined_english = ''
            if pinyin_english:
                defined_pinyin = pinyin_english[0]
                defined_english = pinyin_english[1]
            if not defined_pinyin:
                defined_pinyin = Pinyin().get_pinyin(character, ' ', tone_marks='marks')
                pinyins = defined_pinyin.split(' ')
            else:
                for p in defined_pinyin.split(' '):
                    r = decode_pinyin(p)
                    pinyins.append(r)
            complete_pinyin = ''.join(pinyins)
            # translated = self.translator.translate(character, src='zh-cn')
            # meanings = translated.text
            meanings = pinyin.cedict.translate_word(character)
            english = character + complete_pinyin
            if defined_english:
                english = defined_english
            elif meanings:
                english = '; '.join(meanings)
                # english = meanings[0]
            line_pinyin_english = ','.join((complete_pinyin, english))
            line_english_pinyin = ','.join((english, complete_pinyin))
            line_character_english = ','.join((character, english))
            line_english_character = ','.join((english, character))
            line_character_pinyin = ','.join((character, complete_pinyin))
            results_pinyin_english.append(line_pinyin_english)
            results_english_pinyin.append(line_english_pinyin)
            results_character_english.append(line_character_english)
            results_english_character.append(line_english_character)
            results_character_pinyin.append(line_character_pinyin)
        result1 = '\n'.join(results_pinyin_english)
        result2 = '\n'.join(results_english_pinyin)
        result3 = '\n'.join(results_character_pinyin)
        print(result1)
        print('========================================')
        print(result2)
        print('========================================')
        # print('\n'.join(results_character_english))
        print('========================================')
        # print('\n'.join(results_english_character))
        print('========================================')
        print(result3)
        self.mystr.set(result3)


root = tk.Tk()
root.geometry("800x400+120+120")

app = Application(master=root)
app.mainloop()
