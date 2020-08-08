from tools.kahoot.kahoot_processor import KahootProcessing
from tools.ChineseCardMaker import ChineseCardMaker
cc = ChineseCardMaker()
cc.generate_separate_images()
cc.translate_to_english("动听")

cc.generate_character_pinyin_image()
cc.print_character_pinyin("超市")


def run():
    processing = KahootProcessing()
    processing.create_question_spreadsheet(
        'tools/kahoot/kahoot.csv', 'tools/kahoot/kahoot.txt')
