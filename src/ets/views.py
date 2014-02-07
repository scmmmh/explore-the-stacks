'''
Created on 12 Dec 2013

@author: mhall
'''
from elasticsearch import Elasticsearch
from pyramid.view import view_config
from pywebtools.renderer import render

from ets.models import (DBSession, Book, Topic, Shelf)

def init(config):
    config.add_route('shelves', '/')
    config.add_route('shelf', '/{sid}')
    config.add_route('flickr', 'http://api.flickr.com/services/rest/')

@view_config(route_name='shelves')
@render({'text/html': 'shelves.html'})
def shelves(request):
    dbsession = DBSession()
    shelves = dbsession.query(Shelf)
    if 'q' in request.params and request.params['q'].strip():
        es = Elasticsearch()
        matches = set([int(d['_id']) for d in es.search(index='ets',
                                                   doc_type='shelf',
                                                   body={'query': {'match': {'_all': request.params['q'].strip()}},
                                                     'size': shelves.count()})['hits']['hits']])
    else:
        matches = []
    return {'shelves': shelves,
            'matches': matches}

@view_config(route_name='shelf')
@render({'text/html': 'shelf.html'})
def shelf(request):
    if 'q' in request.params and request.params['q'].strip():
        es = Elasticsearch()
        matches = [int(d['_id']) for d in es.search(index='ets',
                                               doc_type='book',
                                               body={'query': {'match': {'_all': request.params['q'].strip()}},
                                                     'filter': {'term': {'shelf_id_': request.matchdict['sid']}},
                                                     'size': 200})['hits']['hits']]
    else:
        matches = []
    dbsession = DBSession()
    books = dbsession.query(Book).join(Topic.books).filter(Topic.shelf_id==request.matchdict['sid'])
    shelf = dbsession.query(Shelf).filter(Shelf.id==request.matchdict['sid']).first()
    return {'shelf': shelf,
            'books': books,
            'matches': matches}
