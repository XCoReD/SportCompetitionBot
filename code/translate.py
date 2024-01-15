"""on the fly translation with JSON storage of translated pairs"""
from os import walk, path
import json
import deepl
from config import credentials

__translator = None

def _(s:str , language:str = None) -> str:
    global __translator
    if not __translator:
        __translator = MyTranslator()
    return __translator.translate(s, language)

class CachedTranslation():
    language:str
    translations:dict
    def __init__(self, language:str):
        self.language = language
        self.translations = {}

class MyTranslator():
    def __init__(self):
        self.translator = deepl.Translator(credentials["translation"]["deepl_auth_key"])
        self.default_language = credentials["telegram"]["chat"]["language"]
        self.formality = credentials["translation"]["formality"]
        if self.formality and self.formality != "default":
            self.formality = "prefer_" + self.formality
        self.supported_languages = ["en"]
        for l in self.translator.get_target_languages():
            self.supported_languages.append(l.code.lower())
        self.cached_translations = {}
        self.storage_path = path.join(".", "translations")

        self.deserialize()

    def deserialize(self):
        filenames = next(walk(self.storage_path))[2]
        for f in filenames:
            try:
                i = f.index(".json")
                lang = f[:i]
                if len(lang) != 2:
                    continue
                fn = path.join(self.storage_path, f)
                with open(fn, 'r', encoding="utf-8") as f:
                    self.cached_translations[lang] = json.load(f)
            except (IOError) as e:
                print("translate failed to read: %s, %s" % (f, str(e)))

    def dump(self, language: str, entry:dict):
        fn = path.join(self.storage_path, language + ".json")
        with open(fn, 'w', encoding="utf-8") as f:
            json.dump(entry, f, indent=4, ensure_ascii=False)

    def translate(self, text:str, language:str) -> str:
        if not language or language not in self.supported_languages:
            language = self.default_language
        if language == 'en':
            return text
        dict_entry = self.cached_translations.get(language, dict())
        translated = dict_entry.get(text, None)
        if not translated:
            translated = self.translator.translate_text(text, 
                        source_lang='en', target_lang=language, split_sentences='off', preserve_formatting=True, formality=self.formality).text
            dict_entry[text] = translated
            self.dump(language, dict_entry)
        return translated

