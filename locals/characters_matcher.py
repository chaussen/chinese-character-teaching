# Memory Match Game by Nathan Carmine

import pygame
from pygame.locals import *

import time
import random
import os
import pygame.mixer
import pygame.time
import re
from PIL import Image, ImageFont, ImageDraw
from configs import *

# Checks if the cards match using their array indices


def match_check(deck, flipped):
    if deck[CARD_COLUMN_COUNT * flipped[0][1] + flipped[0][0]][1] == deck[CARD_COLUMN_COUNT * flipped[1][1] + flipped[1][0]][1]:
        return True
        # return deck[CARD_COLUMN_COUNT * flipped[0][1] + flipped[0][0]][1]

# Get mouse position, and check which card it's on using division


def card_check(mouse_pos):
    MouseX = mouse_pos[0]
    MouseY = mouse_pos[1]
    CardX = int(MouseX / CARD_WIDTH)
    CardY = int(MouseY / CARD_HEIGHT)
    card = (CardX, CardY)
    return card

# Draw the cards. This is used after initialization and to rehide cards


def card_draw(cards):
    pygame.init()
    screen = pygame.display.set_mode(DISPLAY_SIZE)

    # Place card images in their appropriate spots by multiplying card width & height
    for i in range(CARD_COLUMN_COUNT):
        for j in range(CARD_ROW_COUNT):
            if i + CARD_COLUMN_COUNT * j >= CARD_NUMBER:
                continue
            screen.blit(cards[i + CARD_COLUMN_COUNT * j],
                        (i * CARD_WIDTH, j * CARD_HEIGHT))

# Load the main card images (used in cards_init())


def card_load(name):
    card = f"{CHARACTER_IMAGES_PATH}%s" % name

    # card = "./card_images/%s-spades.png" % char
    card_load = pygame.image.load(card)
    return card_load


def mySqrt(x):
    left, r = 0, x
    while left < r:
        mid = (left + r) // 2
        if mid * mid < x:
            left = mid + 1
        else:
            r = mid
    return left


def find_nearest_two(n):
    root = mySqrt(n)
    answer = n, n
    answer1, answer2, answer3 = (
        root - 1) * root, root * root, (root - 1) * (root + 1)
    if answer2 - n in range(0, 2):
        answer = root, root
    elif answer1 - n in range(0, 2):
        answer = root - 1, root
    elif answer3 - n in range(0, 2):
        answer = root - 1, root + 1
    else:
        minimum = n
        for pair in [(root - 1, root), (root, root), (root - 1, root + 1)]:
            first, second = pair
            if first * second - n < 0:
                continue
            if first * second - n < minimum:
                answer = first, second
                minimum = first * second - n
    return answer


def calculate_card_size(image_count):
    # auto calculate how many one row/column and how big
    # assume each image is square.
    # width / column, height / row. depending on smaller
    smaller, bigger = find_nearest_two(image_count)
    board_width, board_length = DISPLAY_SIZE
    card_side = 0
    if board_width > board_length:
        card_column, card_row = bigger, smaller
        card_side = board_width // card_column
    else:
        card_column, card_row = smaller, bigger
        card_side = board_length // card_row
    global CARD_NUMBER
    global CARD_WIDTH
    global CARD_ROW_COUNT
    global CARD_COLUMN_COUNT
    global CARD_HEIGHT
    CARD_NUMBER = image_count
    CARD_WIDTH = card_side
    CARD_ROW_COUNT = card_row
    CARD_COLUMN_COUNT = card_column
    # CARD_WIDTH = DISPLAY_SIZE[0] // CARD_COLUMN_COUNT
    CARD_HEIGHT = CARD_WIDTH


def cards_init():
    cards = []
    # load all images
    files = os.listdir(f"{CHARACTER_IMAGES_PATH}")
    calculate_card_size(len(files))
    for f in files:
        sequence_number = re.search(FILE_NAME_PATTERN, f).group(1)
        surface = card_load(f)
        surface = pygame.transform.scale(surface, (CARD_WIDTH, CARD_HEIGHT))
        cards.append((surface, sequence_number))
    random.shuffle(cards)

    return cards


def create_card_backs():
    card_backs = []
    for x in range(1, CARD_NUMBER + 1):
        img = Image.new('RGB', (CARD_WIDTH, CARD_HEIGHT),
                        color=(34, 58, 112))
        font = ImageFont.truetype('calibri', CARD_HEIGHT - 100)
        draw = ImageDraw.Draw(img)
        text = f"{str(x)}"
        w, h = font.getsize(text)
        gapx = (CARD_WIDTH - w) // 2
        gapy = (CARD_HEIGHT - h) // 2
        draw.text((gapx, gapy), text, "white", font=font)
        mode = img.mode
        size = img.size
        data = img.tobytes()
        card_back = pygame.image.fromstring(data, size, mode)
        # card_back = pygame.image.load(f"./card_images/{str(x)}.png")
        card_back = pygame.transform.scale(
            card_back, (CARD_WIDTH, CARD_HEIGHT))
        card_backs.append(card_back)
    return card_backs


def main(runs):
    # DISPLAY_SIZE = (750, 905)
    GAME_TITLE = "Character Matcher"
    DESIRED_FPS = 60

    # Setup preliminary pygame stuff
    pygame.init()
    screen = pygame.display.set_mode(DISPLAY_SIZE)
    screen.fill([255, 255, 255])
    pygame.display.update()
    pygame.display.set_caption(GAME_TITLE)

    fps_clock = pygame.time.Clock()

    card_deck = cards_init()  # initialize deck

    # Load card-back image for all cards at first, and have matches slowly unveiled
    # card_backs = create_card_backs()
    # for x in range(1, CARD_NUMBER + 1):
    #     img = Image.open(f"./card_images/{str(x)}.jpg").convert("RGBA")
    #     new_image = Image.new("RGBA", img.size, "WHITE")
    #     new_image.paste(img, (0, 0), img)
    #     new_image.save(f"./card_images/{str(x)}.png")
    #     card_back = pygame.image.load(f"./card_images/{str(x)}.png")
    #     card_back = pygame.transform.scale(
    #         card_back, (CARD_WIDTH, CARD_HEIGHT))
    #     visible_deck.append(card_back)
    visible_deck = create_card_backs()

    card_draw(visible_deck)

    game_run = True  # run the game

    # Ensure the welcome message is displayed only on the first time through
    if runs == 0:
        print("Welcome to Memory Match! Select two cards to flip them and find a match!")
        print("Press 'q' to quit at any time.")
    elif runs == 1:
        print("\n\nNew Game")

    #"Global" variables used throughout the while loop
    flips = []
    found = []
    missed = 0
    first_flip = 0
    second_flip = 0
    t = 1

    while game_run:
        user_input = pygame.event.get()
        pressed_key = pygame.key.get_pressed()

        # Retreives all user input
        for event in user_input:
            # Is the input mouse button pressed down?
            if event.type == pygame.MOUSEBUTTONDOWN:
                # Get position of mouse and put it into card_check
                # to figure out which card mouse is on
                mouse_pos = pygame.mouse.get_pos()
                card_select = card_check(mouse_pos)
                # Make sure card has not been selected before
                if card_select not in flips and card_select not in found:
                    flips.append(card_select)
                    # Put the actual value of the card on the screen (vs just the back)
                    if len(flips) <= 2:
                        if CARD_COLUMN_COUNT * card_select[1] + card_select[0] >= len(card_deck):
                            continue
                        screen.blit(card_deck[CARD_COLUMN_COUNT * card_select[1] + card_select[0]][0],
                                    (CARD_WIDTH * card_select[0], CARD_HEIGHT * card_select[1]))
                        first_flip = time.time()  # First card has been flipped
                    if len(flips) == 2:
                        second_flip = time.time()  # Second card has been flipped
                        # Are the two cards a match?
                        match = match_check(card_deck, flips)
                        if match:
                            # If a match, append coordinates of two cards to found array,
                            # and have them permanently displayed by adding them to the visible deck
                            for i in range(2):
                                found.append(flips[i])
                                visible_deck[CARD_COLUMN_COUNT * flips[i][1] + flips[i][0]
                                             ] = card_deck[CARD_COLUMN_COUNT * flips[i][1] + flips[i][0]][0]
                            print(
                                f"Matches found: {(len(found) / 2)}/{CARD_NUMBER}")
                            t = 0  # Allows user to immediately flip next card
                        else:
                            missed += 1

        # Show the cards only for one second
        if len(flips) >= 2 and time.time() - second_flip > t:
            t = 1
            card_draw(visible_deck)
            flips = []

        # If the user is slow, the card gets flipped back
        elif len(flips) == 1 and time.time() - first_flip > 3:
            card_draw(visible_deck)
            flips = []
            # Unsure if misseses += 1 belongs here - balance question

        # This comes before quitting to avoid video errors
        pygame.display.flip()
        fps_clock.tick(DESIRED_FPS)

        if pressed_key[K_q]:
            game_run = False

        if len(found) == CARD_NUMBER:
            found.append("WIN")
            print("YOU WIN!")
            print(f"Score: {str(missed)} misses")
            # User presses "y" or "n" in the card window
            print("\nPlay again? (y/n)")
            runs = 2

        if runs == 2:  # Win mode of main
            if pressed_key[K_y]:
                main(1)
            elif pressed_key[K_n]:
                game_run = False

    pygame.quit()


main(0)  # Three modes of main: first run (0), not first run (1), win (2)
