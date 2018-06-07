# -*- coding: utf-8 -*-
# Explore The Stacks
#
# Copyright (C) 2013 Mark Hall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
u"""
.. moduleauthor:: Mark Hall <mark.hall@mail.room3b.eu>
"""

from pyramid.config import Configurator
from pyramid_beaker import session_factory_from_settings
from sqlalchemy import engine_from_config

from ets import views, helpers
from ets.models import DBSession

def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    config = Configurator(settings=settings)
    config.include('kajiki.integration.pyramid')
    config.add_static_view('static', 'static', cache_max_age=3600)
    views.init(config, settings)
    config.scan()
    return config.make_wsgi_app()
