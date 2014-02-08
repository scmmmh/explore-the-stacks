'''
Created on 12 Dec 2013

@author: mhall
'''
from elasticsearch import Elasticsearch
from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config
from pywebtools.renderer import render

from ets.models import (DBSession, Book, ShelfMark, Shelf)

def init(config):
    config.add_route('favicon', '/favicon.ico')
    config.add_route('root', '/')
    config.add_route('shelf', '/shelf/{sid}')
    config.add_route('flickr', 'http://api.flickr.com/services/rest/')

@view_config(route_name='root')
def root(request):
    dbsession = DBSession()
    shelf = dbsession.query(Shelf).filter(Shelf.parent_id==None).first()
    raise HTTPFound(request.route_url('shelf', sid=shelf.id))

@render({'text/html': 'shelves.html'})
def shelf_group(request, shelf):
    dbsession = DBSession()
    shelves = dbsession.query(Shelf)
    if shelf:
        shelves = shelves.filter(Shelf.parent_id==shelf.id).order_by(Shelf.order)
    else:
        shelves = shelves.filter(Shelf.parent_id==None).order_by(Shelf.order)
    if 'q' in request.params and request.params['q'].strip():
        es = Elasticsearch()
        matches = set([int(d['_id']) for d in es.search(index='ets',
                                                   doc_type='shelf',
                                                   body={'query': {'match': {'_all': request.params['q'].strip()}},
                                                     'size': shelves.count()})['hits']['hits']])
    else:
        matches = []
    return {'shelf': shelf,
            'shelves': shelves,
            'matches': matches}

@render({'text/html': 'shelf.html'})
def book_shelf(request, shelf):
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
    books = dbsession.query(Book).join(ShelfMark.books).filter(ShelfMark.shelf_id==request.matchdict['sid'])
    return {'shelf': shelf,
            'books': books,
            'matches': matches}

@view_config(route_name='shelf')
def shelves(request):
    dbsession = DBSession()
    shelf = dbsession.query(Shelf).filter(Shelf.id==request.matchdict['sid']).first()
    if shelf.children:
        return shelf_group(request, shelf)
    else:
        return book_shelf(request, shelf)
