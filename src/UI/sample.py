import tkinter as tk
import path_configs
# from character_pinyin_constants import CHARACTER_PINYIN_MAPPING
from character_card_maker import ChineseCardMaker


class Application(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.pack()
        self.create_widgets()
        self.card_maker = ChineseCardMaker()

    def create_widgets(self):
        self.translate = tk.Button(self)
        self.translate["text"] = "Translate to English"
        self.translate["command"] = self.translate_to_english
        self.translate.grid(row=1, column=2)

        self.quit = tk.Button(self, text="QUIT", fg="red",
                              command=self.master.destroy)
        self.quit.grid(row=2, column=2)

        self.entry = tk.Entry(self)
        self.entry.grid(row=0, column=1)
        # self.text = tk.Text(self, borderwidth=0,
        # background="black", foreground="green")

    def generate_separate_images(self):
        self.card_maker.generate_separate_images()

    def translate_to_english(self):
        text = self.entry.get()
        if text:
            translations = self.card_maker.translate_to_english(text)
            # self.Label(self, text='\n'.join(translations)).grid(row=3, column=0)
            # ['是', ['variant of 是[shi4]', '(used in given names)']]
            for translation in translations:
                for line in translation:
                    for i, word in enumerate(line):
                        w = tk.Text(self, borderwidth=0, height=1,
                                    background="black", foreground="green")
                        w.insert(1.0, word)
                        w.grid(row=i, column=1)
                        w.configure(
                            state="disabled")
                    # if tkinter is 8.5 or above you'll want the selection background
                    # to appear like it does when the widget is activated
                    # comment this out for older versions of Tkinter
                        w.configure(
                            inactiveselectbackground=w.cget("selectbackground"))

# cc.generate_separate_images()

# cc.translate_to_english("慈")
    def generate_character_pinyin_image(self):
        translations = self.card_maker.generate_character_pinyin_image()
        tk.Label(self, text='\n'.join(translations)).grid(row=3, column=0)


root = tk.Tk()
app = Application(master=root)
app.mainloop()
