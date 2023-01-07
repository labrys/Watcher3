import gettext
import os
import watcher3

locale_dir = os.path.join(watcher3.PROG_PATH, 'locale')


def get():
    ''' Sets watcher3.LANGUAGES to a dict {'en': <object gettext.translation>}

    Does not return
    '''
    for lang in os.listdir(locale_dir):
        if not os.path.isdir(os.path.join(locale_dir, lang)):
            continue

        watcher3.LANGUAGES[lang] = gettext.translation('watcher', localedir=locale_dir, languages=[lang])

    watcher3.LANGUAGES['en'] = gettext.translation('watcher', localedir=locale_dir, languages=[''], fallback=True)


def install(lang=None):
    ''' Set/install language of choice
    lang (str): language code of language to apply  <optional - default read from config>

    Does not return
    '''

    lang = watcher3.CONFIG['Server']['language'] if not lang else lang

    watcher3.LANGUAGES.get(lang, watcher3.LANGUAGES['en']).install()
    watcher3.LANGUAGE = lang
