'''
#################################
:mod:`ets.views` -- Pyramid Views
#################################

This module contains the view definitions that are used to create the actual
web application for exploring the stacks.

.. moduleauthor: Mark Hall <Mark.Hall@work.room3b.eu>
'''
from elasticsearch import Elasticsearch
from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config
from pywebtools.renderer import render
from random import sample
from sqlalchemy import and_

from ets.models import (DBSession, Book, ShelfMark, Shelf)


def init(config):
    '''Initialise the routes handled by the views.

    The following roots are defined:
    * ``root`` -- ``/``
    * ``shelf`` -- ``/shelf/{sid}``
    '''
    config.add_route('root', '/')
    config.add_route('shelf', '/shelf/{sid}')


@view_config(route_name='root')
def root(request):
    '''The root view simply re-directs to :func:`~ets.views.shelves` with
    the ``{sid}`` set to the id of the root :class:`~ets.models.Shelf`.
    '''
    dbsession = DBSession()
    shelf = dbsession.query(Shelf).filter(Shelf.parent_id==None).first()
    raise HTTPFound(request.route_url('shelf', sid=shelf.id))


@render({'text/html': 'shelves.html'})
def shelf_group(request, shelf, prev, nxt):
    '''The :func:`~ets.views.shelf_group` handles displaying of a
    :class:`~ets.models.Shelf` that contains other :class:`~ets.models.Shelf`.

    It loads the :class:`~ets.models.Shelf`\'s child shelves and then runs a
    query against the ElasticSearch to find which ones match the optional
    query.
    '''
    dbsession = DBSession()
    shelves = dbsession.query(Shelf)
    if shelf:
        shelves = shelves.filter(Shelf.parent_id==shelf.id).order_by(Shelf.order)
    else:
        shelves = shelves.filter(Shelf.parent_id==None).order_by(Shelf.order)
    if 'q' in request.params and request.params['q'].strip():
        try:
            es = Elasticsearch()
            body = {'query': {'match': {'_all': request.params['q'].strip()}},
                    'filter': {'term': {'shelf_id_': request.matchdict['sid']}},
                    'size': shelves.count()}
            matches = set([int(d['_id']) for d in es.search(index='ets',
                                                            doc_type='shelf',
                                                            body=body)['hits']['hits']])
        except:
            matches = []
    else:
        matches = []
    query = dbsession.query(Shelf)
    if shelf.parent_id:
        query = query.filter(Shelf.parent_id==shelf.id)
    keywords = set()
    for kw_shelf in query:
        if kw_shelf.keywords:
            keywords.update([kw for kw in kw_shelf.keywords.split(',')])
    if keywords and len(keywords) > 6:
        keywords = [kw.strip() for kw in sample(keywords, 6)]
    return {'shelf': shelf,
            'prev': prev,
            'next': nxt,
            'shelves': shelves,
            'matches': matches,
            'keywords': keywords}


@render({'text/html': 'shelf.html'})
def book_shelf(request, shelf, prev, nxt):
    '''The :func:`~ets.views.shelf_group` handles displaying of a
    :class:`~ets.models.Shelf` that contains :class:`~ets.models.Book`.

    It loads the :class:`~ets.models.Shelf`\'s :class:`~ets.models.Book` and
    then runs a query against the ElasticSearch to find which ones match the
    optional query.
    '''
    if 'q' in request.params and request.params['q'].strip():
        try:
            es = Elasticsearch()
            matches = [int(d['_id']) for d in es.search(index='ets',
                                                        doc_type='book',
                                                        body={'query': {'match': {'_all': request.params['q'].strip()}},
                                                              'filter': {'term': {'shelf_id_': request.matchdict['sid']}},
                                                              'size': 200})['hits']['hits']]
        except:
            matches = []
    else:
        matches = []
    dbsession = DBSession()
    books = dbsession.query(Book).join(ShelfMark.books).filter(ShelfMark.shelf_id==request.matchdict['sid'])
    if shelf.keywords:
        keywords = [kw.strip() for kw in sample(shelf.keywords.split(','), min(6, len(shelf.keywords.split(','))))]
    else:
        keywords = []
    return {'shelf': shelf,
            'prev': prev,
            'next': nxt,
            'books': books,
            'matches': matches,
            'keywords': keywords}


@view_config(route_name='shelf')
def shelves(request):
    '''Renders the shelf view, using either the :func:`~ets.views.shelf_group`
    or :func`~ets.views.book_shelf` depending on whether the current
    :class:`~wte.models.Shelf` has child shelves or not.
    '''
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
