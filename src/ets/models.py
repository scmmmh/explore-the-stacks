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
from zope.sqlalchemy import ZopeTransactionExtension

DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
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
    parent_id = Column(Integer, ForeignKey('shelves.id', name='shelves_shelves_fk', use_alter=True))
    order = Column(Integer)
    start = Column(Unicode(255))
    end = Column(Unicode(255))
    keywords = Column(Unicode(255))

    shelf_marks = relationship('ShelfMark',
                               primaryjoin='Shelf.id == ShelfMark.shelf_id',
                               order_by='ShelfMark.title',
                               backref=backref('shelf'))
    children = relationship('Shelf', backref=backref('parent', remote_side=[id]),
                            primaryjoin='Shelf.id==Shelf.parent_id')


class ShelfMark(Base):

    __tablename__ = 'shelf_marks'

    id = Column(Integer, primary_key=True)
    shelf_id = Column(Integer, ForeignKey(Shelf.id, name='topics_shelf_fk'))
    title = Column(Unicode(255), index=True)


books_shelf_marks = Table('books_shelf_marks', Base.metadata,
                          Column('book_id', Integer, ForeignKey('books.id', name='books_shelf_marks_book_fk')),
                          Column('shelf_mark_id', Integer, ForeignKey('shelf_marks.id', name='books_shelf_marks_shelf_mark_fk')))

class Book(Base, JsonAttrs):

    __tablename__ = 'books'

    id = Column(Integer, primary_key=True)
    book_identifier = Column(Unicode(255), index=True)
    order = Column(Integer)

    shelf_marks = relationship(ShelfMark,
                               secondary=books_shelf_marks,
                               backref='books')


class Illustration(Base, JsonAttrs):

    __tablename__ = 'illustrations'

    id = Column(Integer, primary_key=True)
    book_id = Column(Integer, ForeignKey(Book.id, name='illustrations_book_fk'), index=True)
    flickr_id = Column(Unicode(255), index=True)
    order = Column(Integer)

    book = relationship(Book,
                        backref=backref('illustrations', order_by='Illustration.order'))
