import re
import threading

from repoze.lru import LRUCache
import six

from routes import request_config
from routes.util import (
    controller_scan,
    RoutesException,
    as_unicode
)
from routes.route import Route


COLLECTION_ACTIONS = ['index', 'create', 'new']
MEMBER_ACTIONS = ['show', 'update', 'delete', 'edit']


def strip_slashes(name):
    """Remove slashes from the beginning and end of a part/URL.
    for example: /index/ --> index; /index --> index; index/ --> index
    """
    if name.startswith('/'):
        name = name[1:]
    if name.endswith('/'):
        name = name[:-1]
    return name


class SubMapperParent(object):
    """Base class for Mapper and SubMapper"""
    def submapper(self, **kargs):
        """Get SubMapper object"""
        return SubMapper(self, **kargs)

    def collection(self, collection_name, resource_name, ):

class SubMapper(object):
    pass