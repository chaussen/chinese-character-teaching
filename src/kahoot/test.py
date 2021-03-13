from easynmt import EasyNMT
model = EasyNMT('opus-mt')

#Translate a single sentence to German
print(model.translate('This is a sentence we want to translate to German', target_lang='de'))

#Translate several sentences to German
sentences = ['You can define a list with sentences.',
             'All sentences are translated to your target language.',
             'Note, you could also mix the languages of the sentences.']
print(model.translate(sentences, target_lang='de'))
pip install torch===1.3.1 torchvision===0.4.2 -f https://download.pytorch.org/whl/torch_stable.html
# from googletrans import Translator
# translator = Translator(raise_exception=True)
# # translator.detect('この文章は日本語で書かれました。')
# # <Detected lang=ja confidence=0.64889508>
# translated = translator.translate('人少', src='zh-cn', dest='en')
# print(translated.extra_data)
# # <Translated src=ko dest=en text=Good evening. pronunciation=Good evening.>
# print(translated.origin)
# print(translated.text)
# translated = translator.translate('人少', dest='ja')
# print(translated.origin)
# print(translated.text)
# # <Translated src=ko dest=ja text=こんにちは。 pronunciation=Kon'nichiwa.>
# translations = translator.translate(
#     ['The quick brown fox', 'jumps over', 'the lazy dog'], dest='ko')
# for translation in translations:
#     print(translation.origin, ' -> ', translation.text)
