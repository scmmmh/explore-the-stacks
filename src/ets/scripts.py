# -*- coding: utf-8 -*-

import json
import logging
import os

from argparse import ArgumentParser
from csv import DictReader
from elasticsearch import Elasticsearch
from gensim import corpora, models
from pyramid.paster import (get_appsettings, setup_logging)
from sqlalchemy import engine_from_config

from ets.models import (DBSession, Base, Book, Topic, Shelf, Illustration)

def init_database(args):
    settings = get_appsettings(args.configuration)
    setup_logging(args.configuration)
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    if args.drop_existing:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    es = Elasticsearch()

def load_books(args):
    settings = get_appsettings(args.configuration)
    setup_logging(args.configuration)
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    dbsession = DBSession()
    with open(args.source) as f:
        books = json.load(f)
        count = 0
        for book_id, book_data in books.items():
            db_book = dbsession.query(Book).filter(Book.book_identifier==book_id).first()
            if not db_book:
                db_book = Book(book_identifier=book_id,
                               shelfmark=book_data['shelfmarks'][0],
                               attrs=book_data)
            else:
                db_book.shelfmark = book_data['shelfmarks'][0]
                db_book.attrs = book_data
            dbsession.add(db_book)
            count = count + 1
            if count % 10000 == 0:
                print '%i books processed' % (count)
                dbsession.commit()
    dbsession.commit()
    
def load_illustrations(args):
    settings = get_appsettings(args.configuration)
    setup_logging(args.configuration)
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    dbsession = DBSession()
    count = 0
    db_book = None
    for path, _, filenames in os.walk('/home/mhall/Documents/Data/British_Library/imagedirectory/'):
        for filename in filenames:
            if not filename.endswith('.tsv'):
                continue
            with open('%s/%s' % (path, filename)) as f:
                reader = DictReader(f, dialect='excel-tab')
                for line in reader:
                    db_book = dbsession.query(Book).filter(Book.book_identifier==line['book_identifier']).first()
                    if db_book:
                        for field in ['date', 'page', 'volume', 'image_idx']:
                            try:
                                line[field] = int(line[field])
                            except ValueError:
                                pass
                        illustration = Illustration(flickr_id=line['flickr_id'],
                                                    attrs=line)
                        db_book.illustrations.append(illustration)
                        dbsession.add(illustration)
                        count = count + 1
            print '%i illustrations loaded' % (count)
            dbsession.commit()

def create_topics(args):
    settings = get_appsettings(args.configuration)
    setup_logging(args.configuration)
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    dbsession = DBSession()
    count = 0
    for book in dbsession.query(Book):
        if not book.topics and book.shelfmark:
            db_topic = dbsession.query(Topic).filter(Topic.title==book.shelfmark).first()
            if not db_topic:
                db_topic = Topic(title=book.shelfmark)
            dbsession.add(db_topic)
            db_topic.books.append(book)
            count = count + 1
            if count % 1000 == 0:
                print '%i books processed' % (count)
                dbsession.commit()
    dbsession.commit()
    print '%i books processed' % (count)

def create_shelves(args):
    settings = get_appsettings(args.configuration)
    setup_logging(args.configuration)
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    dbsession = DBSession()
    shelf = None
    count = 0
    dbsession.query(Topic).update({'shelf_id': None})
    dbsession.query(Shelf).delete()
    dbsession.commit()
    for topic in dbsession.query(Topic).order_by(Topic.title):
        if not shelf:
            shelf = Shelf()
            dbsession.add(shelf)
            shelf.topics.append(topic)
            count = len(topic.books)
        elif count + len(topic.books) > 200:
            shelf = Shelf()
            dbsession.add(shelf)
            shelf.topics.append(topic)
            count = len(topic.books)
        else:
            shelf.topics.append(topic)
            count = count + len(topic.books)
    dbsession.commit()
    for shelf in dbsession.query(Shelf):
        if shelf.topics:
            shelf.start = shelf.topics[0]
            shelf.end = shelf.topics[-1]
    dbsession.commit()

def shorten_shelves(args):
    settings = get_appsettings(args.configuration)
    setup_logging(args.configuration)
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    dbsession = DBSession()
    prefix = None
    for shelf in dbsession.query(Shelf):
        if prefix:
            os.path.commonprefix([prefix, shelf.start.title, shelf.end.title])
        else:
            prefix = os.path.commonprefix([shelf.start.title, shelf.end.title])
    prefix_len = len(prefix)
    for shelf in dbsession.query(Shelf):
        shelf.start.title = shelf.start.title[prefix_len:]
        shelf.end.title = shelf.end.title[prefix_len:]
    dbsession.commit()
        
def index_data(args):
    settings = get_appsettings(args.configuration)
    setup_logging(args.configuration)
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    dbsession = DBSession()
    es = Elasticsearch()
    for book in dbsession.query(Book):
        if book.topics:
            body = {'shelf_id_': [t.shelf.id for t in book.topics]}
            body.update(book.attrs)
            es.index(index='ets',
                     doc_type='book',
                     body=body,
                     id=book.id)
    for shelf in dbsession.query(Shelf):
        es.index(index='ets',
                 doc_type='shelf',
                 body={'start': shelf.start.title,
                       'end': shelf.end.title,
                       'text': '. '.join([title for t in shelf.topics for b in t.books for title in b.attrs['title']])},
                 id=shelf.id)

STOPWORDS = ['a', 'the', 'with', 'and', 'of', 'in', 'by', 'etc', 'illustrations',
             'to', 'from', 'on', 'edition', 'an', 'being', 'illustrated', 'for',
             'de', 'its', 'le', 'du', 'les', 'at', 'appendix', 'some', 'or',
             'other', 'la', 'und', 'das', 'der', 'die', 'des', 'au', 'mit',
             'his', 'her', 'one', 'two', 'three', 'en', 'sur', 'del', 'por',
             'nach', 'auf', 'um', 'which', 'with', 'sobre', 'ii', 'iii', 'iv',
             'vi', 'vii', 'vii', 'ix', 'mr', 'mrs', 'ms', 'during', 'as',
             'edited', 'par', 'dans', 'zum', 'beim', 'et', 'que', 'it', 'first',
             'second', 'third', 'avec', 'including', 'that', 'he', 'she', 'bd',
             'von', 'con', 'al', 'den', 'zur', 'aus', 'los', 'da', 'plates',
             'van', 'het', 'di', 'della', 'dem', 'og', 'och', 'new', 'old', 'el',
             'single', 'im', 'bis', 'four', 'five', 'las', 'los', 'delle', 'dei',
             'aux', 'para', 'sus', 'them', 'me', 'entre', 'us', 'our', 'son',
             'il', 'ses', 'depuis', 'ou', "d'un", 'their', 'ein', u'à', u'á',
             u'és', 'ed', 'tot', 'einer', 'einem', 'eines', 'zu', 'st', 'om' ]
def create_keywords(args):
    class BookCorpus(object):
        def __init__(self, query, dictionary):
            self.query = query
            self.dictionary = dictionary
        
        def __iter__(self):
            for book in self.query:
                doc = []
                for title in book.attrs['title']:
                    for sep in ['.', ',', ';', ':', '-', '_', '?', '!', '(', ')', '[', ']', '{', '}']:
                        title = title.replace(sep, ' ')
                    doc.extend([w.lower() for w in title.split() if w.lower() not in STOPWORDS and len(w) > 1])
                bow = self.dictionary.doc2bow(doc)
                yield bow
    
    settings = get_appsettings(args.configuration)
    setup_logging(args.configuration)
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    dbsession = DBSession()
    dictionary = corpora.dictionary.Dictionary()
    for book in dbsession.query(Book):
        for title in book.attrs['title']:
            for sep in ['.', ',', ';', ':', '-', '_', '?', '!', '(', ')', '[', ']', '{', '}']:
                title = title.replace(sep, ' ')
            dictionary.doc2bow([w.lower() for w in title.split() if w.lower() not in STOPWORDS and len(w) > 1], allow_update=True)
    dictionary.filter_extremes(keep_n=None)
    dictionary.compactify()
    dictionary.save('corpus.dict')
    corpora.MmCorpus.serialize('corpus.mm', BookCorpus(dbsession.query(Book), dictionary))
    dictionary = corpora.dictionary.Dictionary.load('corpus.dict')
    model = models.tfidfmodel.TfidfModel(BookCorpus(dbsession.query(Book), dictionary))
    for shelf in dbsession.query(Shelf):
        text = []
        for topic in shelf.topics:
            for book in topic.books:
                text.extend(book.attrs['title'])
        text = ' '.join(text)
        for sep in ['.', ',', ';', ':', '-', '_', '?', '!', '(', ')', '[', ']', '{', '}']:
            text = text.replace(sep, ' ')
        doc = [w.lower() for w in text.split(' ') if w.lower() not in STOPWORDS and len(w) > 1]
        topics = model[dictionary.doc2bow(doc)]
        topics.sort(key=lambda k: k[1], reverse=True)
        keywords = [dictionary[t[0]] for t in topics[0:5]]
        shelf.keywords = ', '.join([k[0].upper() + k[1:] for k in keywords])
    dbsession.commit()
        

def main():
    root_parser = ArgumentParser(description='ExploreTheStacks console application')
    subparsers = root_parser.add_subparsers()

    parser = subparsers.add_parser('initialise-database')
    parser.add_argument('configuration', help='Experiment Support System configuration file')
    parser.add_argument('--drop-existing', action='store_true', default=False, help='Drop any existing tables')
    parser.set_defaults(func=init_database)
    parser = subparsers.add_parser('load-books')
    parser.add_argument('configuration', help='Experiment Support System configuration file')
    parser.add_argument('source', help='Book meta-data JSON file')
    parser.set_defaults(func=load_books)
    parser = subparsers.add_parser('load-illustrations')
    parser.add_argument('configuration', help='Experiment Support System configuration file')
    parser.add_argument('source', help='Path to the directory containing the illustrations')
    parser.set_defaults(func=load_illustrations)
    parser = subparsers.add_parser('create-topics')
    parser.add_argument('configuration', help='Experiment Support System configuration file')
    parser.set_defaults(func=create_topics)
    parser = subparsers.add_parser('create-shelves')
    parser.add_argument('configuration', help='Experiment Support System configuration file')
    parser.set_defaults(func=create_shelves)
    parser = subparsers.add_parser('shorten-shelves')
    parser.add_argument('configuration', help='Experiment Support System configuration file')
    parser.set_defaults(func=shorten_shelves)
    parser = subparsers.add_parser('index-data')
    parser.add_argument('configuration', help='Experiment Support System configuration file')
    parser.set_defaults(func=index_data)
    parser = subparsers.add_parser('create-keywords')
    parser.add_argument('configuration', help='Experiment Support System configuration file')
    parser.set_defaults(func=create_keywords)

    args = root_parser.parse_args()

    logger = logging.getLogger('mapmaker')
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter('(%(asctime)s)\t%(levelname)s\t%(message)s'))
    logger.addHandler(handler)

    args.func(args)
