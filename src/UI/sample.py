import tkinter as tk
import path_configs
# from character_pinyin_constants import CHARACTER_PINYIN_MAPPING
from character_card_maker import ChineseCardMaker
from kahoot_processor import KahootProcessing


class Application(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.pack()
        self.card_maker = ChineseCardMaker()
        self.processing = KahootProcessing()
        self.create_widgets()
        self.row = 0

    def create_widgets(self):
        self._translate_widget(0)
        self._question_sheet_widget(1)
        self._spreadsheet_widget(2)
        self._separate_image_widget(3)
        self._full_card_widget(4)
        self._quit_widget(5)

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

    def _quit_widget(self, row):
        self.quit = tk.Button(self, text="QUIT", fg="red",
                              command=self.master.destroy)
        self.quit.grid(row=row, column=0)

    def create_question_sheet(self):
        english = self.english_var.get()
        reverse = self.reverse_var.get()
        source = '../kahoot/kahoot.txt'
        destination = ''
        if english is True and reverse is False:
            destination = '../kahoot/kahoot1.csv'
        if english is False and reverse is True:
            destination = '../kahoot/kahoot2.csv'
        if english is False and reverse is False:
            destination = '../kahoot/kahoot3.csv'
        if english is True and reverse is True:
            destination = '../kahoot/kahoot4.csv'

        self.processing.translate_pinyin_question_spreadsheet(
            destination, source, english=english, reverse=reverse)

    def generate_separate_images(self):
        self.card_maker.generate_separate_images()

    def translate_to_english(self):
        text = self.entry.get()
        if text:
            self.card_maker.translate_to_english(text)

    def create_xlsx(self):
        self.processing.generate_mixed_questions(int(self.question_count.get()), '../kahoot/kahoot.csv', [
                                                 '../kahoot/kahoot1.csv', '../kahoot/kahoot2.csv', '../kahoot/kahoot3.csv', '../kahoot/kahoot4.csv'])
        self.processing.convert_to_xlsx('../kahoot/kahoot.csv')

# cc.translate_to_english("慈")
    def generate_character_pinyin_image(self):
        self.card_maker.generate_character_pinyin_image()

    def __get_next_row(self):
        return self.row


root = tk.Tk()
root.geometry("800x400+120+120")

app = Application(master=root)
app.mainloop()
