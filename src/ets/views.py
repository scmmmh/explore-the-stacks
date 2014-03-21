'''
Created on 12 Dec 2013

@author: mhall
'''
from elasticsearch import Elasticsearch
from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config
from pywebtools.renderer import render
from random import sample
from sqlalchemy import and_

from ets.models import (DBSession, Book, ShelfMark, Shelf)

def init(config):
    config.add_route('favicon', '/favicon.ico')
    config.add_route('root', '/')
    config.add_route('shelf', '/shelf/{sid}')

@view_config(route_name='root')
def root(request):
    dbsession = DBSession()
    shelf = dbsession.query(Shelf).filter(Shelf.parent_id==None).first()
    raise HTTPFound(request.route_url('shelf', sid=shelf.id))

@render({'text/html': 'shelves.html'})
def shelf_group(request, shelf, prev, nxt):
    dbsession = DBSession()
    shelves = dbsession.query(Shelf)
    if shelf:
        shelves = shelves.filter(Shelf.parent_id==shelf.id).order_by(Shelf.order)
    else:
        shelves = shelves.filter(Shelf.parent_id==None).order_by(Shelf.order)
    if 'q' in request.params and request.params['q'].strip():
        es = Elasticsearch()
        body = {'query': {'match': {'_all': request.params['q'].strip()}},
                'filter': {'term': {'shelf_id_': request.matchdict['sid']}},
                'size': shelves.count()}
        matches = set([int(d['_id']) for d in es.search(index='ets',
                                                   doc_type='shelf',
                                                   body=body)['hits']['hits']])
    else:
        matches = []
    query = dbsession.query(Shelf)
    if shelf.parent_id:
        query = query.filter(Shelf.parent_id==shelf.id)
    keywords = set()
    for kw_shelf in query:
        keywords.update([kw for kw in kw_shelf.keywords.split(',')])
    keywords = [kw.strip() for kw in sample(keywords, 6)]
    return {'shelf': shelf,
            'prev': prev,
            'next': nxt,
            'shelves': shelves,
            'matches': matches,
            'keywords': keywords}

@render({'text/html': 'shelf.html'})
def book_shelf(request, shelf, prev, nxt):
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
    keywords = [kw.strip() for kw in sample(shelf.keywords.split(','), min(6, len(shelf.keywords.split(','))))]
    return {'shelf': shelf,
            'prev': prev,
            'next': nxt,
            'books': books,
            'matches': matches,
            'keywords': keywords}

@view_config(route_name='shelf')
def shelves(request):
    dbsession = DBSession()
    shelf = dbsession.query(Shelf).filter(Shelf.id==request.matchdict['sid']).first()
    if shelf and shelf.order:
        prev = dbsession.query(Shelf).filter(and_(Shelf.parent_id==shelf.parent_id,
                                                  Shelf.order==shelf.order - 1)).first()
        nxt = dbsession.query(Shelf).filter(and_(Shelf.parent_id==shelf.parent_id,
                                                 Shelf.order==shelf.order + 1)).first()
    else:
        prev = None
        nxt = None
    if shelf.children:
        return shelf_group(request, shelf, prev, nxt)
    else:
        return book_shelf(request, shelf, prev, nxt)
