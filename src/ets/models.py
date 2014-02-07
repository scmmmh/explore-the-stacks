'''
Created on 12 Dec 2013

@author: mhall
'''
import json

from copy import deepcopy
from sqlalchemy import (Column, Integer, Unicode, ForeignKey,
                        UnicodeText, Table)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import (scoped_session, sessionmaker, relationship, backref)

DBSession = scoped_session(sessionmaker())
Base = declarative_base()

class JsonAttrs(object):
    
    _attrs = Column(UnicodeText())
    
    def get_attrs(self):
        if not hasattr(self, '_json_attrs'):
            self._json_attrs = json.loads(self._attrs)
        return self._json_attrs
    
    def set_attrs(self, attrs):
        self._json_attrs = deepcopy(attrs)
        self._attrs = json.dumps(attrs)
    
    attrs = property(get_attrs, set_attrs)

class Shelf(Base):
    
    __tablename__ = 'shelves'
    
    id = Column(Integer, primary_key=True)
    start_id = Column(Integer, ForeignKey('topics.id', name='shelves_start_fk', use_alter=True))
    end_id = Column(Integer, ForeignKey('topics.id', name='shelves_end_fk', use_alter=True))
    keywords = Column(Unicode(255))
    
    topics = relationship('Topic',
                          primaryjoin='Shelf.id==Topic.shelf_id',
                          order_by='Topic.title',
                          backref=backref('shelf'))
    start = relationship('Topic', primaryjoin='Shelf.start_id==Topic.id', uselist=False)
    end = relationship('Topic', primaryjoin='Shelf.end_id==Topic.id', uselist=False)

class Topic(Base):
    
    __tablename__ = 'topics'
    
    id = Column(Integer, primary_key=True)
    shelf_id = Column(Integer, ForeignKey(Shelf.id, name='topics_shelf_fk'))
    title = Column(Unicode(255), index=True)
        
books_topics = Table('books_topics', Base.metadata,
                     Column('book_id', Integer, ForeignKey('books.id', name='books_topics_book_fk')),
                     Column('topic_id', Integer, ForeignKey('topics.id', name='books_topics_topic_fk')))
    
class Book(Base, JsonAttrs):
    
    __tablename__ = 'books'
    
    id = Column(Integer, primary_key=True)
    book_identifier = Column(Unicode(255), index=True)
    shelfmark = Column(Unicode(255), index=True)
    
    prev_id = Column(Integer, ForeignKey('books.id', name='book_prev_fk'))
    next_id = Column(Integer, ForeignKey('books.id', name='book_next_fk'))
    
    prev = relationship('Book', primaryjoin='Book.prev_id==Book.id', uselist=False, remote_side=[id])
    next = relationship('Book', primaryjoin='Book.next_id==Book.id', uselist=False, remote_side=[id])

    topics = relationship(Topic, secondary=books_topics, backref='books')

class Illustration(Base, JsonAttrs):
    
    __tablename__ = 'illustrations'
    
    id = Column(Integer, primary_key=True)
    book_id = Column(Integer, ForeignKey(Book.id, name='illustrations_book_fk'), index=True)
    flickr_id = Column(Unicode(255), index=True)
    order = Column(Integer)
    
    book = relationship(Book,
                        backref=backref('illustrations', order_by='Illustration.order'))
