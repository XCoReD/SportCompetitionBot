"""menu helper class"""
from copy import deepcopy
from typing import List, Dict
from translate import _

class MenuHelper:
    '''Telegram menu with localization on the fly'''
    translation_memo = {}

    @classmethod
    def get_menu(cls, l:str, entry: List[List[Dict[str, str]]], entry_name:str) -> List[List[Dict[str, str]]]:
        if not l:
            return entry
        if entry_name:
            cached_name = entry_name + "_" + l
            if cached_name in cls.translation_memo:
                return cls.translation_memo[cached_name]
        result = []
        for e in entry:
            target = deepcopy(e)
            for t in target:
                t['text'] = _(t['text'], l)
            result.append(target)
        if entry_name:
            cls.translation_memo[cached_name] = result
        return result

    @classmethod
    def remove_menu_entry(cls, menu: List[List[Dict[str, str]]], callback_data_to_remove:int) -> List[List[Dict[str, str]]]:
        result = []
        removed = False
        for m in menu:
            target = deepcopy(m)
            for e in target:
                if e['callback_data'] == callback_data_to_remove:
                    target.remove(e)
                    removed = True
            result.append(target)
        if not removed:
            raise KeyError('callback data not found: ' + callback_data_to_remove)
        return result

    @classmethod
    def set_menu_entry_argument(cls, menu: List[List[Dict[str, str]]], callback_data:int, argument: str) -> List[List[Dict[str, str]]]:
        result = []
        success = False
        for m in menu:
            target = deepcopy(m)
            for e in target:
                if e['callback_data'] == callback_data:
                    t = e['text'] = e['text'] % argument
                    print(e['text'] + " => " + t)
                    e['text'] = t
                    success = True
            result.append(target)
        if not success:
            raise KeyError('callback data not found: ' + callback_data)
        return result
