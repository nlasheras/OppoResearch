from urllib.request import urlopen

import json
import time
from os import path
import os

global_ignore_cache = False
time_between_requests = 0.25
def cached_request(url, cache = None):
    filename = f"cached_requests/{cache}.txt"
    if cache and path.exists(filename) and not global_ignore_cache:
        with open(filename) as f:
            return json.load(f)
    response = urlopen(url)
    data = json.loads(response.read())
    if cache:
        cache_path = cache.split("/")[:-1][0]
        if not path.exists(f"cached_requests/{cache_path}"):
            os.makedirs(f"cached_requests/{cache_path}")
        with open(filename, "w") as f:
            json.dump(data, f)
    time.sleep(time_between_requests)
    return data
