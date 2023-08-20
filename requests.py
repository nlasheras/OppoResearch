from urllib.request import urlopen

import json
import time
from os import path
import os

time_between_requests = 0.25
def cached_request(url, cache = None):
    filename = f"cached_requests/{cache}.txt"
    if cache and path.exists(filename):
        with open(filename) as f:
            return json.load(f)
    response = urlopen(url)
    data = json.loads(response.read())
    if cache:
        cache_path = "/".join(cache.split("/")[:-1])
        if not path.exists(cache_path):
            os.makedirs(cache_path)
        with open(filename, "w") as f:
            json.dump(data, f)
    time.sleep(time_between_requests)
    return data
