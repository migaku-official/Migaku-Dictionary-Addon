import json
from anki.httpclient import HttpClient


DEFAULT_SERVER = 'dicts.migaku.io'


def normalize_url(url):
    if not url.startswith('http'):
        url = 'http://' + url
    while url.endswith('/'):
        url = url[:-1]
    return url


def download_index(server_url=DEFAULT_SERVER):
    server_url = normalize_url(server_url)
    
    index_url = server_url + '/index.json'

    client = HttpClient()
    resp = client.get(index_url)

    if resp.status_code != 200:
        return None

    data = client.streamContent(resp)
    return json.loads(data)
