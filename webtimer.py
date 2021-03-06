#!/usr/bin/env python
"""
Copyright (C) 2014 Chris Spencer (chrisspen at gmail dot com)

Measures download times for all resources on a webpage.

This library is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 3 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
"""
from __future__ import print_function
VERSION = (0, 0, 2)
__version__ = '.'.join(map(str, VERSION))

import os
import sys
import re
import time

try: # Python 2
    import urllib
    import urllib2
    import urlparse
except ImportError: # Python 3
    import urllib.request
    import urllib.parse

from fake_useragent import UserAgent
ua = UserAgent()

JS_URLS = re.compile(r'<\s*script\s+src=[\'"]([^\'"]+)[\'"]', flags=re.DOTALL|re.IGNORECASE)
CSS_URLS = re.compile(r'<\s*link.*?href=[\'"]([^\'"]+)[\'"]', flags=re.DOTALL|re.IGNORECASE)
IMG_URLS = re.compile(r'<img\s+src=[\'"]([^\'"]+)[\'"]', flags=re.DOTALL|re.IGNORECASE)

HTML = 'HTML'
JS = 'Javascript'
CSS = 'CSS'
IMG = 'Image'

ASSET_PATTERNS = (
    (JS, JS_URLS),
    (CSS, CSS_URLS),
    (IMG, IMG_URLS),
)

class WebTimer(object):
    
    def __init__(self, url):
        self.url = url
        self.domain = None
        self.times = {} # {url:download_seconds}
        self.times_by_type = {} # {asset_type:download_seconds}
        self.html = {} # {url:html}
        self.link_types = {} # {type:set([url])}
        
    def measure(self, url, asset_type):
        
        if url.startswith('//'):
            url = 'http:' + url
        elif url.startswith('/'):
            url = 'http://' + self.domain + url
            
        if url not in self.html:
            t0 = time.time()
            # Randomize user-agent and ignore robots.txt to ensure server
            # isn't gaming load times.
            try:
                req = urllib2.Request(url, headers={ 'User-Agent': ua.random })
                html = urllib2.urlopen(req).read()
            except NameError:
                req = urllib.request.Request(url, headers={ 'User-Agent': ua.random })
                html = urllib.request.urlopen(req).read()
            td = time.time() - t0
            self.times[url] = td
            self.times_by_type.setdefault(asset_type, 0)
            self.times_by_type[asset_type] += td
            self.html[url] = html
        return self.html[url]
    
    @property
    def total_download_seconds(self):
        try:
            return sum(self.times.itervalues())
        except AttributeError:
            return sum(self.times.values())
        
    def evaluate(self):
        try:
            self.domain = urlparse.urlparse(url).netloc
        except NameError:
            self.domain = urllib.parse.urlparse(self.url).netloc
        pending = [(HTML, self.url)]
        i = 0
        while pending:
            i += 1
            next_type, next_url = pending.pop(0)
            total = len(pending) + i
            try:
                print ('\rMeasuring %i of %i %.02f%%: %s' \
                    % (i, total, i/float(total)*100, next_url[:60])).ljust(80),
                sys.stdout.flush()
            except AttributeError:
                print (('\rMeasuring %i of %i %.02f%%: %s' \
                    % (i, total, i/float(total)*100, next_url[:60])).ljust(80),
                sys.stdout.flush())
            html = self.measure(url=next_url, asset_type=next_type)
            if next_type == HTML:
                for name, pattern in ASSET_PATTERNS:
                    try:
                        matches = pattern.findall(html)
                    except TypeError:
                        matches = pattern.findall(html.decode("UTF-8"))
                    self.link_types.setdefault(name, set())
                    self.link_types[name].update(matches)
                    for link in set(matches):
                        # Note, we double-check CSS links since our pattern
                        # catches non-CSS URLs.
                        if name == CSS and 'css' not in link.lower():
                            continue
                        if link not in self.html and link not in pending:
                            pending.append((name, link))

if __name__ == '__main__':
    url = sys.argv[1]
    wt = WebTimer(url=url)
    wt.evaluate()
    print ('\n','-'*80,'\nDownload times by URL:')
    fmt = '%%%d.02f %%s' % len('%.02f' % max(wt.times.values()))
    for url, download_time in sorted(wt.times.items(), key=lambda o:o[1]):
        print (fmt % (download_time, url))
    print ('-'*80,'\nDownload times by asset type:')
    fmt = '%%%d.02f %%6.02f%%%% %%s' % len('%.02f' % max(wt.times_by_type.values()))
    for asset_type, download_time in sorted(wt.times_by_type.items(), key=lambda o:o[1]):
        print (fmt % (download_time, download_time/wt.total_download_seconds*100, asset_type))
    print ('-'*80,'\nTotal download seconds: %.02f' % wt.total_download_seconds)
    
