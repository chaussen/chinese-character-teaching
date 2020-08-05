## Synopsis

Chinese Character Teaching Tools

## Tools

### Chinese Maker

It makes character flash cards in batches.

Execute the lines in _test.py_:


```ChineseCardMaker().generate_separate_images()```

```ChineseCardMaker().generate_character_pinyin_image()```

The command will generate images with characters and pinyins set in _CharacterPinyinMapping_, and create files in the folders defined inside _configs_: *CHARACTER_IMAGE_FILE_NAME_PREFIX*, *PINYIN_IMAGE_FILE_NAME_PREFIX*, *CHARACTER_PINYIN_FOLDER*

### Kahoot Processor

It generates Excel sheet quickly for [Kahoot](https://kahoot.it) question uploading. It takes a lot of time to add questions on Kahoot, so it is easier to use Excel spreadsheet to add questions in a large amount.

## Motivation

To save time and efforts for Chinese character card making with pinyin.

## Installation

Pure python packages are required for the tool.

1. Install Python3
2. PIL: for image making
3. pinyin: for translation
4. xpinyin: for default pinyin
5. pygame: for the matching game only
6. csv: for Kahoot spreadsheet file generation
7. xlsxwriter: for Kahoot spreadsheet file generation

1-4 are necessary for card making. 5 is optional for game.  
3, 4, 6 and 7 are also required for Kahoot processor.

## API Reference

See the _test.py_.

## Tests

See the _test.py_.

## Contributors

[John Ni](chaussen@gmail.com)

The matching game is based on this [Memory_Match](https://github.com/ncarmine/Memory_Match)

## License

John Ni

[Memory_Match](https://github.com/ncarmine/Memory_Match)