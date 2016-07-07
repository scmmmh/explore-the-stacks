'''
######################################
:mod:`ets.helpers` -- Template Helpers
######################################

This module provides helper functions for use within the Genshi templates.

.. moduleauthor: Mark Hall <Mark.Hall@work.room3b.eu>
'''
import json


def format_title(title):
    '''Cleans up the formatting of book titles, removing square brackets that
    indicate meta-data.
    '''
    if '[' in title:
        if title[0] != '[':
            title = title[0:title.find('[')]
        elif title[-1] == ']':
            title = title[1:-1]
    return title


def shelf_title(shelf):
    '''Determines the appropriate title for a :class:`~wte.models.Shelf`.
    '''
    if shelf.start == shelf.end:
        return shelf.start
    else:
        return '%s - %s' % (shelf.start, shelf.end)