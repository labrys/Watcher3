import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib'))

if sys.version_info < (3, 0, 0):
    print('Python 3.0 or newer required. Currently {}.'.format(sys.version.split(' ')[0]))
    sys.exit(1)

import watcher3         # noqa
watcher3.PROG_PATH = os.path.dirname(os.path.realpath(__file__))
os.chdir(watcher3.PROG_PATH)
watcher3.SCRIPT_PATH = os.path.join(watcher3.PROG_PATH, os.path.basename(__file__))
if os.name == 'nt':
    watcher3.PLATFORM = 'windows'
else:
    watcher3.PLATFORM = '*nix'

import argparse     # noqa
import locale       # noqa
import logging      # noqa
import webbrowser   # noqa
import shutil       # noqa

import cherrypy     # noqa
from cherrypy.process.plugins import Daemonizer, PIDFile    # noqa

if __name__ == '__main__':

    # have to set locale for date parsing
    try:
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    except Exception as e:
        try:
            # for windows
            locale.setlocale(locale.LC_ALL, 'English_United States.1252')
        except Exception as e:
            logging.warning('Unable to set locale. Date parsing may not work correctly.')
            print('\033[33m Unable to set locale. Date parsing may not work correctly.\033[0m')

    # parse user-passed arguments
    parser = argparse.ArgumentParser(description='Watcher Server App')
    parser.add_argument('-d', '--daemon', help='Run the server as a daemon.', action='store_true')
    parser.add_argument('-a', '--address', help='Network address to bind to.')
    parser.add_argument('-p', '--port', help='Port to bind to.', type=int)
    parser.add_argument('-b', '--browser', help='Open browser on launch.', action='store_true')
    parser.add_argument('--userdata', help='Userdata dir containing database, config, etc.', type=str)
    parser.add_argument('-c', '--conf', help='Location of config file.', type=str)
    parser.add_argument('-l', '--log', help='Directory in which to create log files.', type=str)
    parser.add_argument('--db', help='Absolute path to database file.', type=str)
    parser.add_argument('--plugins', help='Directory in which plugins are stored.', type=str)
    parser.add_argument('--posters', help='Directory in which posters are stored.', type=str)
    parser.add_argument('--pid', help='Directory in which to store pid file.', type=str)
    parser.add_argument('--stdout', help='Print all log messages to STDOUT.', action='store_true')
    passed_args = parser.parse_args()

    if passed_args.userdata:
        watcher3.USERDATA = passed_args.userdata
        watcher3.CONF_FILE = os.path.join(passed_args.userdata, 'config.cfg')
        watcher3.DB_FILE = os.path.join(passed_args.userdata, 'watcher.sqlite')
        if not os.path.exists(watcher3.USERDATA):
            os.mkdir(watcher3.USERDATA)
            print("Specified userdata directory created.")
        else:
            print("Userdata directory exists, continuing.")
    if passed_args.db:
        watcher3.DB_FILE = passed_args.db
        if not os.path.exists(os.path.dirname(watcher3.DB_FILE)):
            os.makedirs(os.path.dirname(watcher3.DB_FILE))
    else:
        watcher3.DB_FILE = os.path.join(watcher3.PROG_PATH, watcher3.DB_FILE)
    if passed_args.conf:
        watcher3.CONF_FILE = passed_args.conf
        if not os.path.exists(os.path.dirname(watcher3.CONF_FILE)):
            os.makedirs(os.path.dirname(watcher3.CONF_FILE))
    else:
        watcher3.CONF_FILE = os.path.join(watcher3.PROG_PATH, watcher3.CONF_FILE)
    if passed_args.log:
        watcher3.LOG_DIR = passed_args.log
    if passed_args.plugins:
        watcher3.PLUGIN_DIR = passed_args.plugins
    if passed_args.posters:
        watcher3.POSTER_DIR = passed_args.posters
    else:
        watcher3.POSTER_DIR = os.path.join(watcher3.USERDATA, 'posters')
        
    # set up db connection
    from watcher3 import sqldb
    watcher3.sql = sqldb.SQL()
    watcher3.sql.update_database()

    # set up config file on first launch
    from watcher3 import config
    if not os.path.isfile(watcher3.CONF_FILE):
        print(f'\033[33m## Config file not found. Creating new basic config {watcher3.CONF_FILE}. Please review settings. \033[0m')
        config.new_config()
    else:
        print('Config file found, merging any new options.')
        config.merge_new_options()
    config.load()

    # Set up logging
    from watcher3 import log
    log.start(watcher3.LOG_DIR, passed_args.stdout or False)
    logging = logging.getLogger(__name__)
    cherrypy.log.error_log.propagate = True
    cherrypy.log.access_log.propagate = False

    # clean mako cache
    try:
        print('Clearing Mako cache.')
        shutil.rmtree(watcher3.MAKO_CACHE)
    except FileNotFoundError:  # noqa: F821 : Flake8 doesn't know about some built-in exceptions
        pass
    except Exception as e:
        print('\033[31m Unable to clear Mako cache. \033[0m')
        print(e)

    # Finish core application
    from watcher3 import config, scheduler, version
    from watcher3.app import App
    watcher3.updater = version.manager()

    # Set up server
    if passed_args.address:
        watcher3.SERVER_ADDRESS = passed_args.address
    else:
        watcher3.SERVER_ADDRESS = str(watcher3.CONFIG['Server']['serverhost'])
    if passed_args.port:
        watcher3.SERVER_PORT = passed_args.port
    else:
        watcher3.SERVER_PORT = watcher3.CONFIG['Server']['serverport']

    # mount and configure applications
    if watcher3.CONFIG['Server']['customwebroot']:
        watcher3.URL_BASE = watcher3.CONFIG['Server']['customwebrootpath']

    watcher3.SERVER_URL = f'http://{watcher3.SERVER_ADDRESS}:{watcher3.SERVER_PORT}{watcher3.URL_BASE}'

    root = cherrypy.tree.mount(App(), f'{watcher3.URL_BASE}/', 'core/conf_app.ini')

    # Start plugins
    if passed_args.daemon:
        if watcher3.PLATFORM == '*nix':
            Daemonizer(cherrypy.engine).subscribe()
        elif watcher3.PLATFORM == 'windows':
            from cherrypysytray import SysTrayPlugin  # noqa
            menu_options = (('Open Browser', None, lambda *args: webbrowser.open(watcher3.SERVER_URL)),)
            systrayplugin = SysTrayPlugin(cherrypy.engine, 'core/favicon.ico', 'Watcher', menu_options)
            systrayplugin.subscribe()
            systrayplugin.start()

    scheduler.create_plugin()

    if passed_args.pid:
        PIDFile(cherrypy.engine, passed_args.pid).subscribe()

    # SSL certs
    if watcher3.CONFIG['Server']['ssl_cert'] and watcher3.CONFIG['Server']['ssl_key']:
        logging.info('SSL Certs are enabled. Server will only be accessible via https.')
        print('SSL Certs are enabled. Server will only be accessible via https.')
        ssl_conf = {'server.ssl_certificate': watcher3.CONFIG['Server']['ssl_cert'],
                    'server.ssl_private_key': watcher3.CONFIG['Server']['ssl_key'],
                    'tools.https_redirect.on': True
                    }
        try:
            from OpenSSL import SSL # noqa
        except ImportError as e:
            ssl_conf['server.ssl_module'] = 'builtin'
            m = '''
Using built-in SSL module. This may result in a large amount of
logged error messages even though everything is working correctly.
You may avoid this by installing the pyopenssl module.'''
            print(m)
            logging.info(m)
            pass
        cherrypy.config.update(ssl_conf)

    # Open browser
    if passed_args.browser or watcher3.CONFIG['Server']['launchbrowser']:
        logging.info('Launching web browser.')
        a = 'localhost' if watcher3.SERVER_ADDRESS == '0.0.0.0' else watcher3.SERVER_ADDRESS
        webbrowser.open(f'http://{a}:{watcher3.SERVER_PORT}{watcher3.URL_BASE}')

    # start engine
    cherrypy.config.update('core/conf_global.ini')
    cherrypy.engine.signals.subscribe()
    cherrypy.engine.start()
    os.chdir(watcher3.PROG_PATH)  # have to do this for the daemon
    cherrypy.engine.block()

# pylama:ignore=E402
