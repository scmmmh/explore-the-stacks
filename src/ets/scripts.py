# -*- coding: utf-8 -*-

import json
import logging
import os

from argparse import ArgumentParser
from csv import DictReader
from elasticsearch import Elasticsearch
from pyramid.paster import (get_appsettings, setup_logging)
from sqlalchemy import engine_from_config
from sqlalchemy.orm import sessionmaker

from ets.models import (Base, Book, ShelfMark, Shelf, Illustration)

def init_database(args):
    logger = logging.getLogger('explorethestacks')
    logger.info('Initialising the database')
    settings = get_appsettings(args.configuration)
    setup_logging(args.configuration)
    engine = engine_from_config(settings, 'sqlalchemy.')
    if args.drop_existing:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    logger.info('Database initialised')

def load_books(args):
    logger = logging.getLogger('explorethestacks')
    logger.info('Loading books')
    settings = get_appsettings(args.configuration)
    setup_logging(args.configuration)
    engine = engine_from_config(settings, 'sqlalchemy.')
    dbsession = sessionmaker(bind=engine)()
    with open(args.source) as f:
        books = json.load(f)
        count = 0
        for book_data in books:
            dbsession.add(Book(book_identifier=book_data['identifier'],
                               attrs=book_data))
            count = count + 1
            if count % 10000 == 0:
                dbsession.commit()
                logger.debug('%i books loaded' % (count))
    dbsession.commit()
    logger.info('%i books loaded' % (count))
    
def load_illustrations(args):
    logger = logging.getLogger('explorethestacks')
    logger.info('Loading illustrations')
    settings = get_appsettings(args.configuration)
    setup_logging(args.configuration)
    engine = engine_from_config(settings, 'sqlalchemy.')
    dbsession = sessionmaker(bind=engine)()
    count = 0
    db_book = None
    for path, _, filenames in os.walk(args.source):
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
                        if count % 10000 == 0:
                            logger.debug('%i illustrations loaded' % (count))
            dbsession.commit()
    logger.info('%i illustrations loaded' % (count))

def filter_books(args):
    logger = logging.getLogger('explorethestacks')
    logger.info('Filtering books')
    settings = get_appsettings(args.configuration)
    setup_logging(args.configuration)
    engine = engine_from_config(settings, 'sqlalchemy.')
    dbsession = sessionmaker(bind=engine)()
    count = 0
    filter_count = 0
    for book in dbsession.query(Book):
        if not book.illustrations:
            dbsession.delete(book)
            filter_count = filter_count + 1
        count = count + 1
        if count % 10000 == 0:
            logger.debug('%i books processed' % (count))
            dbsession.commit()
    dbsession.commit()
    logger.info('%i books filtered' % (filter_count))
        
def extract_shelfmarks(args):
    logger = logging.getLogger('explorethestacks')
    logger.info('Extracting shelf-marks')
    settings = get_appsettings(args.configuration)
    setup_logging(args.configuration)
    engine = engine_from_config(settings, 'sqlalchemy.')
    dbsession = sessionmaker(bind=engine)()
    count = 0
    for book in dbsession.query(Book):
        for title in book.attrs['shelfmarks']:
            shelfmark = dbsession.query(ShelfMark).filter(ShelfMark.title==title).first()
            if not shelfmark:
                shelfmark = ShelfMark(title=title)
            dbsession.add(shelfmark)
            shelfmark.books.append(book)
        count = count + 1
        if count % 10000 == 0:
            logger.debug('%i books processed' % (count))
            dbsession.commit()
    dbsession.commit()
    logger.debug('%i books processed' % (count))
    prefix_len = len(os.path.commonprefix([sm.title for sm in dbsession.query(ShelfMark)]))
    for shelfmark in dbsession.query(ShelfMark):
        shelfmark.title = shelfmark.title[prefix_len:]
    dbsession.commit()
    logger.info('Shelf-marks extracted')

def create_shelves(args):
    logger = logging.getLogger('explorethestacks')
    logger.info('Creating shelves')
    settings = get_appsettings(args.configuration)
    setup_logging(args.configuration)
    engine = engine_from_config(settings, 'sqlalchemy.')
    dbsession = sessionmaker(bind=engine)()
    shelf = None
    book_count = 0
    dbsession.commit()
    idx = 0
    count = 0
    for shelf_mark in dbsession.query(ShelfMark).order_by(ShelfMark.title):
        if not shelf:
            idx = idx + 1
            shelf = Shelf(order=idx)
            dbsession.add(shelf)
            shelf.shelf_marks.append(shelf_mark)
            book_count = len(shelf_mark.books)
        elif book_count + len(shelf_mark.books) > 200:
            idx = idx + 1
            shelf = Shelf(order=idx)
            dbsession.add(shelf)
            shelf.shelf_marks.append(shelf_mark)
            book_count = len(shelf_mark.books)
        else:
            shelf.shelf_marks.append(shelf_mark)
            book_count = book_count + len(shelf_mark.books)
        count = count + 1
        if count % 10000 == 0:
            dbsession.commit()
            logger.debug('%s shelfmarks processed' % (count))
    dbsession.commit()
    logger.debug('%s shelfmarks processed' % (count))
    logger.debug('Creating shelf hierarchy')
    while dbsession.query(Shelf).filter(Shelf.parent_id==None).count() > 50:
        idx = 0
        parent_shelf = None
        child_count = 0
        for shelf in dbsession.query(Shelf).filter(Shelf.parent_id==None).order_by(Shelf.order):
            if not parent_shelf:
                idx = idx + 1
                parent_shelf = Shelf(order=idx)
                dbsession.add(parent_shelf)
                shelf.parent = parent_shelf
                child_count = child_count + 1
            elif child_count > 50:
                parent_shelf = Shelf(order=idx)
                dbsession.add(parent_shelf)
                shelf.parent = parent_shelf
                child_count = 1
            else:
                shelf.parent = parent_shelf
                child_count = child_count + 1
    root_shelf = Shelf()
    dbsession.add(root_shelf)
    for shelf in dbsession.query(Shelf).filter(Shelf.parent_id==None):
        if shelf != root_shelf:
            shelf.parent = root_shelf
    dbsession.commit()
    logger.debug('Creating shelf titles')
    def create_titles(shelf):
        if shelf.children:
            for child in shelf.children:
                create_titles(child)
            shelf.start = shelf.children[0].start
            shelf.end = shelf.children[-1].end
        elif shelf.shelf_marks:
            shelf.start = shelf.shelf_marks[0].title
            shelf.end = shelf.shelf_marks[-1].title
    root_shelf = dbsession.query(Shelf).filter(Shelf.parent_id==None).first()
    create_titles(root_shelf)
    root_shelf.start = 'Explore the Stacks'
    root_shelf.end = 'Explore the Stacks'
    dbsession.commit()
    logger.info('Shelves created')

def recursive_text(shelf):
    text = []
    if shelf.children:
        for child in shelf.children:
            text.extend(recursive_text(child))
    elif shelf.shelf_marks:
        text = [t for shelf_mark in shelf.shelf_marks for book in shelf_mark.books for t in book.attrs['title']]
    return text

def index_data(args):
    logger = logging.getLogger('explorethestacks')
    logger.info('Indexing data')
    settings = get_appsettings(args.configuration)
    setup_logging(args.configuration)
    engine = engine_from_config(settings, 'sqlalchemy.')
    dbsession = sessionmaker(bind=engine)()
    es = Elasticsearch()
    count = 0
    for book in dbsession.query(Book):
        if book.shelf_marks:
            body = {'shelf_id_': [sm.shelf.id for sm in book.shelf_marks]}
            body.update(book.attrs)
            es.index(index='ets',
                     doc_type='book',
                     body=body,
                     id=book.id)
            count = count + 1
            if count % 1000 == 0:
                logger.debug('%i books indexed' % (count))
    logger.info('%i books indexed' % (count))
    count = 0
    for shelf in dbsession.query(Shelf):
        es.index(index='ets',
                 doc_type='shelf',
                 body={'start': shelf.start,
                       'end': shelf.end,
                       'shelf_id_': shelf.parent_id,
                       'text': ' '.join(recursive_text(shelf))},
                 id=shelf.id)
        count = count + 1
        if count % 10 == 0:
            logger.debug('%i shelves indexed' % (count))
    logger.info('%i shelves indexed' % (count))

def create_keywords(args):
    import nltk
    from gensim import corpora, models
    nltk.data.path.append('./')
    STOPWORDS = nltk.corpus.stopwords.words('english') + nltk.corpus.stopwords.words('german') + \
                nltk.corpus.stopwords.words('french') + nltk.corpus.stopwords.words('italian') + \
                nltk.corpus.stopwords.words('spanish') + ['etc', 'new']
    sentence_tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')
    word_tokenizer = nltk.tokenize.TreebankWordTokenizer()
    class BookCorpus(object):
        def __init__(self, query, dictionary):
            self.query = query
            self.dictionary = dictionary
        
        def __iter__(self):
            for book in self.query:
                words = [w.lower() for title in book.attrs['title'] for s in sentence_tokenizer.tokenize(title) for w in word_tokenizer.tokenize(s) if w.lower() not in STOPWORDS and len(w) > 1]
                bow = self.dictionary.doc2bow(words)
                yield bow
    
    logger = logging.getLogger('explorethestacks')
    logger.info('Creating keywords')
    settings = get_appsettings(args.configuration)
    setup_logging(args.configuration)
    engine = engine_from_config(settings, 'sqlalchemy.')
    dbsession = sessionmaker(bind=engine)()
    logger.info('Creating dictionary')
    dictionary = corpora.dictionary.Dictionary()
    for book in dbsession.query(Book):
        words = [w.lower() for title in book.attrs['title'] for s in sentence_tokenizer.tokenize(title) for w in word_tokenizer.tokenize(s) if w.lower() not in STOPWORDS and len(w) > 1]
        dictionary.doc2bow(words, allow_update=True)
    dictionary.filter_extremes(keep_n=None)
    dictionary.compactify()
    dictionary.save('corpus.dict')
    logger.info('Creating corpus')
    corpora.MmCorpus.serialize('corpus.mm', BookCorpus(dbsession.query(Book), dictionary))
    dictionary = corpora.dictionary.Dictionary.load('corpus.dict')
    model = models.tfidfmodel.TfidfModel(BookCorpus(dbsession.query(Book), dictionary))
    logger.info('Processing shelves')
    for shelf in dbsession.query(Shelf):
        text = ' '.join(recursive_text(shelf))
        for sep in ['.', ',', ';', ':', '-', '_', '?', '!', '(', ')', '[', ']', '{', '}']:
            text = text.replace(sep, ' ')
        doc = [w.lower() for w in text.split(' ') if w.lower() not in STOPWORDS and len(w) > 1]
        topics = model[dictionary.doc2bow(doc)]
        topics.sort(key=lambda k: k[1], reverse=True)
        keywords = [dictionary[t[0]] for t in topics[0:10]]
        shelf.keywords = ', '.join([k[0].upper() + k[1:] for k in keywords])
    dbsession.commit()
    logger.info('Keywords created')
        

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
    parser = subparsers.add_parser('filter-books')
    parser.add_argument('configuration', help='Experiment Support System configuration file')
    parser.set_defaults(func=filter_books)
    parser = subparsers.add_parser('extract-shelfmarks')
    parser.add_argument('configuration', help='Experiment Support System configuration file')
    parser.set_defaults(func=extract_shelfmarks)
    parser = subparsers.add_parser('create-shelves')
    parser.add_argument('configuration', help='Experiment Support System configuration file')
    parser.set_defaults(func=create_shelves)
    parser = subparsers.add_parser('index-data')
    parser.add_argument('configuration', help='Experiment Support System configuration file')
    parser.set_defaults(func=index_data)
    parser = subparsers.add_parser('create-keywords')
    parser.add_argument('configuration', help='Experiment Support System configuration file')
    parser.set_defaults(func=create_keywords)

    args = root_parser.parse_args()

    args.func(args)
