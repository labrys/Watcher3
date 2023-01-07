import urllib.request
import watcher3
import logging
from watcher3.helpers import Url

logging = logging.getLogger(__name__)


default_socket = urllib.request.socket.socket
bypass_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
proxy_socket = urllib.request.socket.socket

on = False


def create():
    ''' Starts proxy connection
    Sets global on to True

    Does not return
    '''
    global on
    if not watcher3.CONFIG['Server']['Proxy']['enabled']:
        return

    logging.info('Creating proxy connection.')

    host = watcher3.CONFIG['Server']['Proxy']['host']
    port = watcher3.CONFIG['Server']['Proxy']['port']
    user = watcher3.CONFIG['Server']['Proxy']['user'] or None
    password = watcher3.CONFIG['Server']['Proxy']['pass'] or None

    if watcher3.CONFIG['Server']['Proxy']['type'] == 'socks5':
        logging.info(f'Creating socket for SOCKS5 proxy at {host}:{port}')
        if user and password:
            addr = f'socks5://{user}:{password}@{host}:{port}'
        else:
            addr = f'socks5://{host}:{port}'

        proxies = {'http': addr, 'https': addr}
        Url.proxies = proxies

        on = True
    elif watcher3.CONFIG['Server']['Proxy']['type'] == 'socks4':
        logging.info(f'Creating socket for SOCKS4 proxy at {host}:{port}')
        if user and password:
            addr = f'socks4://{user}:{password}@{host}:{port}'
        else:
            addr = f'socks4://{host}:{port}'

        proxies = {'http': addr, 'https': addr}
        Url.proxies = proxies

        on = True
    elif watcher3.CONFIG['Server']['Proxy']['type'] == 'http(s)':
        logging.info(f'Creating HTTP(S) proxy at {host}:{port}')
        protocol = host.split(':')[0]

        proxies = {}

        if user and password:
            url = f'{user}:{password}@{host}:{port}'
        else:
            url = f'{host}:{port}'

        proxies['http'] = url

        if protocol == 'https':
            proxies['https'] = url
        else:
            logging.warning('HTTP-only proxy. HTTPS traffic will not be tunneled through proxy.')

        Url.proxies = proxies

        on = True
    else:
        logging.warning('Invalid proxy type {}'.format(watcher3.CONFIG['Server']['Proxy']['type']))
        return


def destroy():
    ''' Ends proxy connection
    Sets global on to False

    Does not return
    '''
    global on
    if on:
        logging.info('Closing proxy connection.')
        Url.proxies = None
        on = False
        return
    else:
        return


def whitelist(url):
    ''' Checks if url is in whitelist
    url (str): url to check against whitelist

    Returns bool
    '''
    whitelist = watcher3.CONFIG['Server']['Proxy']['whitelist'].split(',')

    if whitelist == ['']:
        return False

    for i in whitelist:
        if url.startswith(i.strip()):
            logging.info(f'{url} in proxy whitelist, will bypass proxy connection.')
            return True
        else:
            continue
    return False


def bypass(request):
    ''' Temporaily turns off proxy for single request.
    request (object): urllib.request request object

    Restores the default urllib.request socket and uses the default opener to send request.
    When finished restores the proxy socket. If using an http/s proxy the socket is
        restored to the original, so it never changes anyway.

    Should always be inside a try/except block just like any url request.

    Returns object urllib.request response
    '''

    urllib.request.socket.socket = default_socket

    response = bypass_opener.open(request)
    result = response.read().decode('utf-8')
    response.close()

    urllib.request.socket.socket = proxy_socket

    return result
