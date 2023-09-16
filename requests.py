from urllib.request import urlopen

import json
import time
from os import path
import os

global_ignore_cache = False
time_between_requests = 0.25

def __get_cache_path(url):
    cache_path = url.split('://')[1]
    if 'netrunnerdb.com' in cache_path:
        cache_path = cache_path.replace('api/2.0/public/', '')
        cache_path = cache_path.replace('api/v3/public/', '')
    return cache_path
 
def __get_expiration_time(url):
    if 'netrunnerdb.com' in url:
        return 30 * 24 * 3600 
    return 24 * 3600 

def cached_request(url, use_cache = True):
    cache = __get_cache_path(url)
    filename = f"cached_requests/{cache}"
    if not filename.endswith('json'):
        filename += '.json'
    if use_cache and path.exists(filename) and not global_ignore_cache:
        mtime = path.getmtime(filename)
        now = int(time.time())
        elapsed = now - mtime
        print(f"elapsed {filename} = {elapsed}")
        if now - mtime < __get_expiration_time(url):
            with open(filename) as f:
                return json.load(f)
    try:
        response = urlopen(url)
    except Exception as e:
        print(e)
        return None

    data = json.loads(response.read())
    if use_cache:
        cache_path = '/'.join(cache.split("/")[:-1])
        if not path.exists(f"cached_requests/{cache_path}"):
            os.makedirs(f"cached_requests/{cache_path}")
        with open(filename, "w") as f:
            json.dump(data, f)
    time.sleep(time_between_requests)
    return data
