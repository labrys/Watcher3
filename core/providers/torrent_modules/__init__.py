import os
for module in os.listdir(os.path.dirname(os.path.realpath(__file__))):
    if module[-3:] == '.py' and module[0] not in ('.', '_'):
        __import__(f'core.providers.torrent_modules.{module[:-3]}')
