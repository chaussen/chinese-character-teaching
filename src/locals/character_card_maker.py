#!/usr/bin/env python3
from PIL import ImageFont, ImageDraw, Image, ImageOps
import pinyin.cedict
from configs import *
import os
from xpinyin import Pinyin
import path_configs
from character_pinyin_constants import CHARACTER_PINYIN_MAPPING
from character_pinyin_constants import decode_pinyin


class ChineseCardMaker:
    def __init__(self):
        path_configs.show_real_path()

    def save_image_to_path(self, image, filename):
        if not os.path.exists(os.path.dirname(filename)):
            try:
                os.makedirs(os.path.dirname(filename))
            except OSError as err:  # Guard against race condition
                print("OS error: {0}".format(err))
        image.save(filename)

    def initialize_character_card(self, img, j):
        # initialize image
        single_img = Image.new('RGB', (CARD_SIDE_LENGTH, CARD_SIDE_LENGTH),
                               color=CARD_BACKGROUND_COLOR)
        single_draw = ImageDraw.Draw(single_img)
        middle_point = CARD_SIDE_LENGTH // 2
        coord1 = [(0, middle_point), (CARD_SIDE_LENGTH, middle_point)]
        coord2 = [(middle_point, 0), (middle_point, CARD_SIDE_LENGTH)]
        coord3 = [(0, 0), (CARD_SIDE_LENGTH, CARD_SIDE_LENGTH)]
        coord4 = [(CARD_SIDE_LENGTH, 0), (0, CARD_SIDE_LENGTH)]
        single_draw.line(coord1, fill=CARD_GRID_COLOR, width=CARD_GRID_WIDTH)
        single_draw.line(coord2, fill=CARD_GRID_COLOR, width=CARD_GRID_WIDTH)
        single_draw.line(coord3, fill=CARD_GRID_COLOR, width=CARD_GRID_WIDTH)
        single_draw.line(coord4, fill=CARD_GRID_COLOR, width=CARD_GRID_WIDTH)
        # expand border
        single_img = ImageOps.expand(single_img, 1)
        img.paste(single_img, (j * CARD_SIDE_LENGTH, 0))
        # return img

    def add_pinyin_header(self, characters, gap, path):
        pinyins = self.print_character_pinyin(characters)
        max_ph = 0
        pinyin_font = ImageFont.truetype(PINYIN_FONT, PINYIN_FONT_SIZE)
        for p in pinyins:
            max_ph = max(max_ph, pinyin_font.getsize(p)[1])

        file_name = f"{path}{characters}.jpg"
        character_font = ImageFont.truetype(
            CHARACTER_FONT, CHARACTER_FONT_SIZE)
        # pw, ph = pinyin_font.getsize(pinyin)
        coordinates = (CARD_SIDE_LENGTH * len(characters),
                       CARD_SIDE_LENGTH + max_ph + gap)
        img = Image.new('RGB', coordinates, color=CARD_BACKGROUND_COLOR)
        draw = ImageDraw.Draw(img)

        for i, character in enumerate(characters):
            # loop each single character and draw them
            single_img = Image.new('RGB', (CARD_SIDE_LENGTH, CARD_SIDE_LENGTH),
                                   color=CARD_BACKGROUND_COLOR)
            single_draw = ImageDraw.Draw(single_img)
            middle_point = CARD_SIDE_LENGTH // 2
            coord1 = [(0, middle_point), (CARD_SIDE_LENGTH, middle_point)]
            coord2 = [(middle_point, 0), (middle_point, CARD_SIDE_LENGTH)]
            coord3 = [(0, 0), (CARD_SIDE_LENGTH, CARD_SIDE_LENGTH)]
            coord4 = [(CARD_SIDE_LENGTH, 0), (0, CARD_SIDE_LENGTH)]
            coord5 = [(0, 0), (CARD_SIDE_LENGTH, 0)]
            coord6 = [(CARD_SIDE_LENGTH, 0),
                      (CARD_SIDE_LENGTH, CARD_SIDE_LENGTH)]
            coord7 = [(CARD_SIDE_LENGTH, 0), (CARD_SIDE_LENGTH,
                                              CARD_SIDE_LENGTH + max_ph + gap)]
            single_draw.line(coord1, fill=CARD_GRID_COLOR,
                             width=CARD_GRID_WIDTH)
            single_draw.line(coord2, fill=CARD_GRID_COLOR,
                             width=CARD_GRID_WIDTH)
            single_draw.line(coord3, fill=CARD_GRID_COLOR,
                             width=CARD_GRID_WIDTH)
            single_draw.line(coord4, fill=CARD_GRID_COLOR,
                             width=CARD_GRID_WIDTH)
            single_draw.line(coord5, fill=CARD_GRID_COLOR,
                             width=CARD_GRID_WIDTH)
            single_draw.line(coord6, fill=CARD_GRID_COLOR,
                             width=CARD_GRID_WIDTH)
            # expand border
            img.paste(single_img, (i * CARD_SIDE_LENGTH, gap + max_ph))
            draw.line(coord7, fill=CARD_GRID_COLOR, width=CARD_GRID_WIDTH)
            # paste a blank grid to the background
            # get coordinates of top left based on card and character width
            cw, ch = character_font.getsize(character)
            gapx = (CARD_SIDE_LENGTH - cw) // 2
            gapy = (CARD_SIDE_LENGTH - ch) // 2 + max_ph
            # draw characters with offset
            current_gapx = gapx + i * (cw + 2 * gapx)
            draw.text((current_gapx, gapy), character,
                      CHARACTER_COLOR, font=character_font)
            try:
                p = pinyins[i]
            except IndexError as e:
                print(f"{pinyins} with no space: {e}")
                raise e
            pw, ph = pinyin_font.getsize(p)
            # img.paste(pinyin_image, (i * CARD_SIDE_LENGTH, 0))
            gapx = (CARD_SIDE_LENGTH - pw) // 2
            gapy = gap
            # draw characters with offset
            current_gapx = gapx + i * (pw + 2 * gapx)
            draw.text((current_gapx, gapy), p,
                      CHARACTER_COLOR, font=pinyin_font)
        # save
        img = ImageOps.expand(img, 1)
        self.save_image_to_path(img, file_name)
        # img.save(file_name)

    def initialize_pinyin_card(self, img, j):
        single_img = Image.new('RGB', (CARD_SIDE_LENGTH, CARD_SIDE_LENGTH),
                               color=CARD_BACKGROUND_COLOR)
        img.paste(single_img, (j * CARD_SIDE_LENGTH, 0))
        # return img

    def draw_image(self, number, font_file, font_size,
                   characters, file_name_prefix, is_grid):
        coordinates = (CARD_SIDE_LENGTH * len(characters), CARD_SIDE_LENGTH)
        img = Image.new('RGB', coordinates, color=CARD_BACKGROUND_COLOR)
        draw = ImageDraw.Draw(img)
        # initialize font
        font = ImageFont.truetype(font_file, font_size)
        # loop each single character and draw them
        joined = ''.join(characters)
        name = f"{file_name_prefix}{joined}_{str(number)}"
        file_name = f"{name}.jpg"
        for j in range(len(characters)):
            # get one character and actual width, height based on the font
            single = characters[j]
            w, h = font.getsize(single)
            (width, baseline), (offset_x, offset_y) = font.font.getsize(single)
            print(f"{single}: {w}, {h}")
            print(f"{single}: {(width, baseline)}, {(offset_x, offset_y)}")

            # paste a blank grid to the background
            self.initialize_character_card(
                img, j) if is_grid else self.initialize_pinyin_card(img, j)
            # get coordinates of top left based on card and character width
            gapx = (CARD_SIDE_LENGTH - w) // 2
            gapy = (CARD_SIDE_LENGTH - h) // 2
            # draw characters with offset
            current_gapx = gapx + j * (w + 2 * gapx)
            draw.text((current_gapx, gapy), single, CHARACTER_COLOR, font=font)
            # save
        # img.save(file_name)
        self.save_image_to_path(img, file_name)

    def generate_separate_images(self):
        for i, characters in enumerate(CHARACTER_PINYIN_MAPPING):
            self.draw_image(i, CHARACTER_FONT, CHARACTER_FONT_SIZE, characters,
                            CHARACTER_IMAGE_FILE_NAME_PREFIX, True)
            pinyins = self.print_character_pinyin(characters)
            self.draw_image(i, PINYIN_FONT, PINYIN_FONT_SIZE, pinyins,
                            PINYIN_IMAGE_FILE_NAME_PREFIX, False)

    def generate_character_pinyin_image(self):
        for i, zi in enumerate(CHARACTER_PINYIN_MAPPING):
            self.add_pinyin_header(zi, 5, CHARACTER_PINYIN_FOLDER)

    def print_character_pinyin(self, characters):
        pinyin = CHARACTER_PINYIN_MAPPING.get(characters, '')
        pinyins = []
        pinyin_nums = []
        if not pinyin:
            pinyin = Pinyin().get_pinyin(characters, ' ', tone_marks='marks')
            pinyin_num = Pinyin().get_pinyin(characters, ' ',
                                             tone_marks='numbers')
            pinyins = pinyin.split(' ')
            pinyin_nums = pinyin_num.split(' ')
        else:
            for p in pinyin.split(' '):
                r = decode_pinyin(p)
                pinyins.append(r)
        print(f'''"{characters}": "{''.join(pinyin_nums)}",''')
        return pinyins

    def translate_to_english(self, characters):
        translations = pinyin.cedict.all_phrase_translations(characters)
        for i, translation in enumerate(translations):
            print(f"index: {i}: {translation}; type: {type(translation)}")
        return translations
