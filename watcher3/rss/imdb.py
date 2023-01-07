import watcher3
from watcher3 import searcher
from watcher3.movieinfo import TheMovieDatabase
from watcher3.library import Manage
from watcher3.helpers import Url
from datetime import datetime
import json
import logging
import os
import csv

logging = logging.getLogger(__name__)


data_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'imdb')
date_format = '%Y-%m-%d'


def sync():
    ''' Syncs CSV lists from IMDB

    Does not return
    '''

    movies_to_add = []
    library = [i[2] for i in watcher3.sql.quick_titles()]

    try:
        record = json.loads(watcher3.sql.system('imdb_sync_record'))
    except Exception as e:
        record = {}

    for url in watcher3.CONFIG['Search']['Watchlists']['imdbcsv']:
        if url[-6:] not in ('export', 'export/'):
            logging.warning(f'{url} does not look like a valid imdb list')
            continue

        list_id = 'ls' + ''.join(filter(str.isdigit, url))
        logging.info(f'Syncing rss IMDB watchlist {list_id}')

        last_sync = datetime.strptime((record.get(list_id) or '2000-01-01'), date_format)

        try:
            csv_text = Url.open(url).text
            watchlist = [dict(i) for i in csv.DictReader(csv_text.splitlines())][::-1]

            record[list_id] = watchlist[0]['Created']

            for movie in watchlist:
                pub_date = datetime.strptime(movie['Created'], date_format)

                if last_sync > pub_date:
                    break

                imdbid = movie['Const']
                if imdbid not in library and imdbid not in movies_to_add:
                    logging.info('Found new watchlist movie {}'.format(movie['Title']))
                    movies_to_add.append(imdbid)

        except Exception as e:
            logging.warning(f'Unable to sync list {list_id}')

    movies = []
    for imdbid in movies_to_add:
        movie = TheMovieDatabase._search_imdbid(imdbid)
        if not movie:
            logging.warning(f'{imdbid} not found on TheMovieDB. Cannot add.')
            continue
        else:
            movie = movie[0]
        logging.info('Adding movie {} {} from IMDB watchlist.'.format(movie['title'], movie['imdbid']))
        movie['year'] = movie['release_date'][:4] if movie.get('release_date') else 'N/A'
        movie['origin'] = 'IMDB'

        added = Manage.add_movie(movie)
        if added['response']:
            if movie['year'] != 'N/A':
                movies.append(movie)

    if watcher3.CONFIG['Search']['searchafteradd']:
        for movie in movies:
            searcher.search(movie)

    logging.info('Storing last synced date.')
    if watcher3.sql.row_exists('SYSTEM', name='imdb_sync_record'):
        watcher3.sql.update('SYSTEM', 'data', json.dumps(record), 'name', 'imdb_sync_record')
    else:
        watcher3.sql.write('SYSTEM', {'data': json.dumps(record), 'name': 'imdb_sync_record'})
    logging.info('IMDB sync complete.')
