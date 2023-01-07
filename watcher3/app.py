import cherrypy
import watcher3
from watcher3 import ajax, scheduler, plugins, localization, api
from watcher3.auth import AuthController
from watcher3.postprocessing import Postprocessing
import os
import json
from mako.template import Template
import logging

import sys
import time

locale_dir = os.path.join(watcher3.PROG_PATH, 'locale')


class App:

    @cherrypy.expose
    def __init__(self):
        self.auth = AuthController()
        self.postprocessing = Postprocessing()
        self.api = api.API()

        if watcher3.CONFIG['Server']['authrequired']:
            self._cp_config = {
                'auth.require': []
            }

        self.ajax = ajax.Ajax()
        localization.get()
        localization.install()

        # point server toward custom 404
        cherrypy.config.update({
            'error_page.404': self.error_page_404
        })

        # Lock down settings if required
        if watcher3.CONFIG['Server']['adminrequired']:
            self.settings._cp_config['auth.require'] = [watcher3.auth.is_admin]

        if watcher3.CONFIG['Server']['checkupdates']:
            scheduler.AutoUpdateCheck.update_check(install=False)

    def https_redirect(self=None):
        ''' Cherrypy tool to redirect http:// to https://

        Use as before_handler when https is enabled for the server.

        Enable in config as {'tools.https_redirect.on': True}

        '''
        if cherrypy.request.scheme == 'http':
            raise cherrypy.HTTPRedirect(cherrypy.url().replace('http:', 'https:'), status=302)

    cherrypy.tools.https_redirect = cherrypy.Tool('before_handler', https_redirect)

    def defaults(self):
        defaults = {'head': self.head(),
                    'navbar': self.nav_bar(current=sys._getframe().f_back.f_code.co_name),
                    'url_base': watcher3.URL_BASE
                    }
        return defaults

    # All dispatching methods from here down

    status_template = Template(filename='templates/library/status.html', module_directory=watcher3.MAKO_CACHE)
    manage_template = Template(filename='templates/library/manage.html', module_directory=watcher3.MAKO_CACHE)
    import_template = Template(filename='templates/library/import.html', module_directory=watcher3.MAKO_CACHE)
    couchpotato_template = Template(filename='templates/library/import/couchpotato.html', module_directory=watcher3.MAKO_CACHE)
    kodi_template = Template(filename='templates/library/import/kodi.html', module_directory=watcher3.MAKO_CACHE)
    plex_template = Template(filename='templates/library/import/plex.html', module_directory=watcher3.MAKO_CACHE)
    directory_template = Template(filename='templates/library/import/directory.html', module_directory=watcher3.MAKO_CACHE)
    stats_template = Template(filename='templates/library/stats.html', module_directory=watcher3.MAKO_CACHE)

    add_movie_template = Template(filename='templates/add_movie.html', module_directory=watcher3.MAKO_CACHE)

    server_template = Template(filename='templates/settings/server.html', module_directory=watcher3.MAKO_CACHE)
    search_template = Template(filename='templates/settings/search.html', module_directory=watcher3.MAKO_CACHE)
    quality_template = Template(filename='templates/settings/quality.html', module_directory=watcher3.MAKO_CACHE)
    categories_template = Template(filename='templates/settings/categories.html', module_directory=watcher3.MAKO_CACHE)
    languages_template = Template(filename='templates/settings/languages.html', module_directory=watcher3.MAKO_CACHE)
    indexers_template = Template(filename='templates/settings/indexers.html', module_directory=watcher3.MAKO_CACHE)
    downloader_template = Template(filename='templates/settings/downloader.html', module_directory=watcher3.MAKO_CACHE)
    postprocessing_template = Template(filename='templates/settings/postprocessing.html', module_directory=watcher3.MAKO_CACHE)
    plugins_template = Template(filename='templates/settings/plugins.html', module_directory=watcher3.MAKO_CACHE)
    logs_template = Template(filename='templates/settings/logs.html', module_directory=watcher3.MAKO_CACHE)
    system_template = Template(filename='templates/settings/system.html', module_directory=watcher3.MAKO_CACHE)

    shutdown_template = Template(filename='templates/system/shutdown.html', module_directory=watcher3.MAKO_CACHE)
    restart_template = Template(filename='templates/system/restart.html', module_directory=watcher3.MAKO_CACHE)
    update_template = Template(filename='templates/system/update.html', module_directory=watcher3.MAKO_CACHE)

    fourohfour_template = Template(filename='templates/404.html', module_directory=watcher3.MAKO_CACHE)
    head_template = Template(filename='templates/head.html', module_directory=watcher3.MAKO_CACHE)
    navbar_template = Template(filename='templates/navbar.html', module_directory=watcher3.MAKO_CACHE)

    @cherrypy.expose
    def default(self):
        return self.library('status')

    @cherrypy.expose
    def _test(self):
        return 'This is not the page you are looking for.'

    @cherrypy.expose
    def library(self, *path):
        page = path[0] if len(path) > 0 else 'status'

        if page == 'status':

            categories_count = watcher3.sql.get_library_count('category')
            status_count = watcher3.sql.get_library_count('status')
            status_count['Finished'] = status_count.get('Finished', 0) + status_count.get('Disabled', 0)
            if 'Disabled' in status_count:
                del status_count['Disabled']

            return App.status_template.render(profiles=watcher3.CONFIG['Quality']['Profiles'].keys(), categories=watcher3.CONFIG['Categories'].keys(),
                                              status_count=status_count, categories_count=categories_count,
                                              languages = watcher3.CONFIG['Languages'].keys(), **self.defaults())
        elif page == 'manage':
            movies = watcher3.sql.get_user_movies()
            return App.manage_template.render(movies=movies, profiles=watcher3.CONFIG['Quality']['Profiles'].keys(),
                                              categories=watcher3.CONFIG['Categories'].keys(), **self.defaults())
        elif page == 'import':
            subpage = path[1] if len(path) > 1 else None

            if not subpage:
                return App.import_template.render(**self.defaults())
            elif subpage == 'couchpotato':
                return App.couchpotato_template.render(sources=watcher3.SOURCES, profiles=watcher3.CONFIG['Quality']['Profiles'].keys(),
                                                       categories=watcher3.CONFIG['Categories'].keys(), **self.defaults())
            elif subpage == 'kodi':
                return App.kodi_template.render(sources=watcher3.SOURCES, profiles=watcher3.CONFIG['Quality']['Profiles'].keys(),
                                                categories=watcher3.CONFIG['Categories'].keys(), **self.defaults())
            elif subpage == 'plex':
                return App.plex_template.render(sources=watcher3.SOURCES, profiles=watcher3.CONFIG['Quality']['Profiles'].keys(),
                                                categories=watcher3.CONFIG['Categories'].keys(), **self.defaults())
            elif subpage == 'directory':
                try:
                    start_dir = os.path.expanduser('~')
                    file_list = [i for i in os.listdir(start_dir) if os.path.isdir(os.path.join(start_dir, i)) and not i.startswith('.')]
                except Exception as e:
                    start_dir = watcher3.PROG_PATH
                    file_list = [i for i in os.listdir(start_dir) if os.path.isdir(os.path.join(start_dir, i)) and not i.startswith('.')]
                file_list.append('..')
                return App.directory_template.render(sources=watcher3.SOURCES, profiles=watcher3.CONFIG['Quality']['Profiles'].keys(),
                                                     current_dir=start_dir, file_list=file_list,
                                                     categories=watcher3.CONFIG['Categories'].keys(), **self.defaults())
            else:
                return self.error_page_404()
        elif page == 'stats':
            App.stats_template = Template(filename='templates/library/stats.html', module_directory=watcher3.MAKO_CACHE)

            return App.stats_template.render(categories=watcher3.CONFIG['Categories'].keys(), **self.defaults())
        else:
            return self.error_page_404()

    @cherrypy.expose
    def add_movie(self):
        return App.add_movie_template.render(profiles=[(k, v.get('default', False)) for k, v in watcher3.CONFIG['Quality']['Profiles'].items()], categories=watcher3.CONFIG['Categories'].keys(), **self.defaults())

    @cherrypy.expose
    def settings(self, *path):
        page = path[0] if len(path) > 0 else 'server'

        if page == 'server':
            themes = [i[:-4] for i in os.listdir('static/css/themes/') if i.endswith('.css') and os.path.isfile(os.path.join(watcher3.PROG_PATH, 'static/css/themes', i))]
            return App.server_template.render(config=watcher3.CONFIG['Server'], themes=themes, version=watcher3.CURRENT_HASH or '', languages=watcher3.LANGUAGES.keys(), **self.defaults())
        elif page == 'search':
            return App.search_template.render(config=watcher3.CONFIG['Search'], **self.defaults())
        elif page == 'quality':
            return App.quality_template.render(config=watcher3.CONFIG['Quality'], sources=watcher3.SOURCES, **self.defaults())
        elif page == 'categories':
            return App.categories_template.render(config=watcher3.CONFIG['Categories'], sources=watcher3.SOURCES, **self.defaults())
        elif page == 'languages':
            return App.languages_template.render(config=watcher3.CONFIG['Languages'], **self.defaults())
        elif page == 'indexers':
            for indexer in watcher3.CONFIG['Indexers']['TorzNab'].values():
                logging.debug(indexer)
            return App.indexers_template.render(config=watcher3.CONFIG['Indexers'], **self.defaults())
        elif page == 'downloader':
            return App.downloader_template.render(config=watcher3.CONFIG['Downloader'], **self.defaults())
        elif page == 'postprocessing':
            return App.postprocessing_template.render(config=watcher3.CONFIG['Postprocessing'], os=watcher3.PLATFORM, **self.defaults())
        elif page == 'plugins':
            plugs = plugins.list_plugins()
            return App.plugins_template.render(config=watcher3.CONFIG['Plugins'], plugins=plugs, **self.defaults())
        elif page == 'logs':
            logdir = os.path.join(watcher3.PROG_PATH, watcher3.LOG_DIR)
            logfiles = [i for i in os.listdir(logdir) if os.path.isfile(os.path.join(logdir, i))]
            return App.logs_template.render(logdir=logdir, logfiles=logfiles, **self.defaults())
        elif page == 'download_log':
            if len(path) > 1:
                l = os.path.join(os.path.abspath(watcher3.LOG_DIR), path[1])
                return cherrypy.lib.static.serve_file(l, 'application/x-download', 'attachment')
            else:
                raise cherrypy.HTTPError(400)
        elif page == 'system':
            tasks = {}
            for name, obj in watcher3.scheduler_plugin.task_list.items():
                tasks[name] = {'name': name,
                               'interval': obj.interval,
                               'last_execution': obj.last_execution,
                               'enabled': obj.timer.is_alive() if obj.timer else False}

            system = {'database': {'file': watcher3.DB_FILE,
                                   'size': os.path.getsize(watcher3.DB_FILE) / 1024
                                   },
                      'config': {'file': watcher3.CONF_FILE},
                      'system': {'path': watcher3.PROG_PATH,
                                 'arguments': sys.argv,
                                 'version': sys.version[:5]}
                      }
            t = int(time.time())
            dt = time.strftime('%a, %B %d, %Y %H:%M:%S %z', time.localtime(t))
            
            return App.system_template.render(config=watcher3.CONFIG['System'], tasks=json.dumps(tasks), system=system, server_time=[dt, t], **self.defaults())
        else:
            return self.error_page_404()
    settings._cp_config = {}

    @cherrypy.expose
    def system(self, *path, **kwargs):
        if len(path) == 0:
            return self.error_page_404()

        page = path[0]

        if page == 'shutdown':
            return App.shutdown_template.render(**self.defaults())
        if page == 'restart':
            return App.restart_template.render(**self.defaults())
        if page == 'update':
            return App.update_template.render(updating=watcher3.UPDATING, **self.defaults())

    @cherrypy.expose
    def error_page_404(self, *args, **kwargs):
        return App.fourohfour_template.render(**self.defaults())

    def head(self):
        return App.head_template.render(url_base=watcher3.URL_BASE, uitheme=watcher3.CONFIG['Server']['uitheme'], notifications=json.dumps([i for i in watcher3.NOTIFICATIONS if i is not None]), language=watcher3.LANGUAGE)

    def nav_bar(self, current=None):
        username = cherrypy.session.get(watcher3.SESSION_KEY)
        return App.navbar_template.render(url_base=watcher3.URL_BASE, current=current, username=username)
