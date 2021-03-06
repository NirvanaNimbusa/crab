# Copyright (C) 2012-2013 Science and Technology Facilities Council.
# Copyright (C) 2015-2018 East Asian Observatory.
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

from logging.handlers import RotatingFileHandler
import os
import socket
import sys

from cherrypy.lib.reprconf import Config

from crab.store.file import CrabStoreFile
from crab.store.sqlite import CrabStoreSQLite


def read_crabd_config():
    """Determine Crab server configuration.

    This returns a CherryPy configuration dictionary, with
    values read from the config files and environment variables."""

    config = Config()
    config.update({
        'global': {
            'engine.autoreload.on': False,
            'server.socket_port': 8000,
            'server.socket_host': '0.0.0.0',
        },
        'crab': {
            'home': os.path.join(sys.prefix, 'share', 'crab'),
            'base_url': None,
        },
        'email': {
            'server': 'mailhost',
            'from': 'Crab Daemon',
            'subject_ok': 'Crab notification',
            'subject_warning': 'Crab notification (WARNING)',
            'subject_error': 'Crab notification (ERROR)',
        },
        'notify': {
            'timezone': 'UTC',
            'daily': '0 0 * * *',
        },
        'store': {
            'type': 'sqlite',
            'file': '/var/lib/crab/crab.db',
        },
        'access_log': {
            'max_size': 10,
            'backup_count': 10,
        },
        'error_log': {
            'max_size': 10,
            'backup_count': 10,
        },
    })

    env = os.environ
    sysconfdir = env.get('CRABSYSCONFIG', '/etc/crab')
    userconfdir = env.get('CRABUSERCONFIG', os.path.expanduser('~/.crab'))

    try:
        config.update(os.path.join(sysconfdir, 'crabd.ini'))
    except IOError:
        pass

    try:
        config.update(os.path.join(userconfdir, 'crabd.ini'))
    except IOError:
        pass

    if 'CRABHOME' in env:
        config['crab']['home'] = env['CRABHOME']

    config['/res'] = {
        'tools.staticdir.on': True,
        'tools.staticdir.dir': config['crab']['home'] + '/res',
        'tools.staticdir.content_types': {
            'css': 'text/css',
            'eot': 'application/vnd.ms-fontobject',
            'js': 'application/javascript',
            'png': 'image/png',
            'svg': 'image/svg+xml',
            'ttf': 'application/x-font-ttf',
            'woff': 'application/font-woff',
            'woff2': 'font/woff2',
        },
    }

    if 'base_url' not in config['crab'] or config['crab']['base_url'] is None:
        config['crab']['base_url'] = (
            'http://' + socket.getfqdn() + ':' +
            str(config['global']['server.socket_port']))

    return config


def construct_log_handler(filename, log_config):
    return RotatingFileHandler(
        filename,
        maxBytes=log_config['max_size'] * 1024 * 1024,
        backupCount=log_config['backup_count'])


def construct_store(storeconfig, outputstore=None):
    """Constructs a storage backend from the given dictionary."""

    if storeconfig['type'] == 'sqlite':
        store = CrabStoreSQLite(storeconfig['file'], outputstore)

    elif storeconfig['type'] == 'mysql':
        # Only import the MySQL store module when required in case the
        # mysql.connector module isn't installed.
        from crab.store.mysql import CrabStoreMySQL
        store = CrabStoreMySQL(host=storeconfig['host'],
                               database=storeconfig['database'],
                               user=storeconfig['user'],
                               password=storeconfig['password'],
                               outputstore=outputstore)

    elif storeconfig['type'] == 'file':
        store = CrabStoreFile(storeconfig['dir'])

    else:
        raise Exception('Unknown output store type: ' + storeconfig['type'])

    return store
