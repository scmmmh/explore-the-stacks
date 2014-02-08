'''
Created on 12 Dec 2013

@author: mhall
'''

import json

def format_title(title):
    if '[' in title:
        if title[0] != '[':
            title = title[0:title.find('[')]
        elif title[-1] == ']':
            title = title[1:-1]
    return title

def shelf_title(shelf):
    if shelf.start == shelf.end:
        return shelf.start
    else:
        return '%s - %s' % (shelf.start, shelf.end)