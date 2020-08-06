#!/usr/bin/env python3
from character_card_maker import ChineseCardMaker
cc = ChineseCardMaker()
cc.generate_separate_images()
cc.translate_to_english("动听")

cc.generate_character_pinyin_image()

cc.print_character_pinyin("守")
