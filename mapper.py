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

    def collection(self, collection_name, resource_name, path_prefix=None,
                   member_prefix='/{id}', controller=None,
                   collection_actions=COLLECTION_ACTIONS,
                   member_actions=MEMBER_ACTIONS, member_options=None,
                   **kwargs):
        """Create a submapper that represents a collection"""
        if controller is None:
            controller = resource_name or collection_name

        if path_prefix is None:
            if collection_name is None:
                path_prefix_str = ''
            else:
                path_prefix_str = '/{collection_name}'
        else:
            if collection_name is None:
                path_prefix_str = "{pre}"
            else:
                path_prefix_str = "{pre}/{collection_name}"

        # generate what will be the path prefix for the collection
        path_prefix = path_prefix_str.format(pre=path_prefix,
                                             collection_name=collection_name)

        collection = SubMapper(self, collection_name=collection_name,
                               resource_name=resource_name,
                               path_prefix=path_prefix, controller=controller,
                               actions=collection_actions, **kwargs)

        collection.member = SubMapper(collection, path_prefix=member_prefix,
                                      actions=member_actions,
                                      **(member_options or {}))

        return collection


class SubMapper(SubMapperParent):
    """Partial mapper for use with_options"""
    def __init__(self, obj, resource_name=None, collection_name=None,
                 actions=None, formatted=None, **kwargs):
        self.kwargs = kwargs
        self.obj = obj
        self.collection_name = collection_name
        self.member = None
        self.resource_name = resource_name \
            or getattr(obj, 'resource_name', None) \
            or kwargs.get('controller', None) \
            or getattr(obj, 'controller', None)
        if formatted is not None:
            self.formatted = formatted
        else:
            self.formatted = getattr(obj, 'formatted', None)
            if self.formatted is None:
                self.formatted = True
        self.add_actions(actions or [], **kwargs)

    def add_actions(self, actions, **kwargs):
        [getattr(self, action)(**kwargs) for action in actions]

    def connect(self, routename, path=None, **kwargs):
        newkargs = {}
        _routename = routename
        _path = path
        for key, value in six.iteritems(self.kwargs):
            if key == 'path_prefix':
                if path is not None:
                    # if there's a name_prefix, add it to the route name
                    # and if there's a path_prefix
                    _path = ''.join((self.kwargs[key], path))
                else:
                    _path = ''.join((self.kwargs[key], routename))
            elif key == 'name_prefix':
                if path is not None:
                    # if there's a name_prefix, add it to the route name
                    # and if there's a path_prefix
                    _routename = ''.join((self.kwargs[key], routename))
                else:
                    _routename = None
            elif key in kwargs:
                if isinstance(value, dict):
                    newkargs[key] = dict(value, **kwargs[key])  # merge dicts
                else:
                    # Originally used this form:
                    # newkargs[key] = value + kwargs[key]
                    # New version avoids the inheritance concatenation issue
                    # with submappers. Only prefixes concatenate, everything
                    # else overrides in submappers.
                    newkargs[key] = kwargs[key]
            else:
                newkargs[key] = self.kwargs[key]
        for key in kwargs:
            if key not in self.kwargs:
                newkargs[key] = kwargs[key]

        newargs = (_routename, _path)
        return self.obj.connect(*newargs, **newkargs)

    def link(self, rel=None, name=None, action=None, method='GET',
             formatted=None, **kwargs):
        """Generates a named route information"""
        if formatted or (formatted is None and self.formatted):
            suffix = '{.format}'
        else:
            suffix = ''

        return self.connect(name or (rel + '_' + self.resource_name),
                            '/' + (rel or name) + suffix,
                            action=action or rel or name,
                            **_kwargs_with_conditions(kwargs, method))

    def action(self, name=None, action=None, method='GET', formatted=None,
               **kwargs):
        """Generates a named route at the base path of a submapper"""
        if formatted or (formatted is None and self.formatted):
            suffix = '{.format}'
        else:
            suffix = ''
        return self.connect(name or (action + '_' + self.resource_name),
                            suffix,
                            action=action or name,
                            **_kwargs_with_conditions(kwargs, method))

    def new(self, **kwargs):
        return self.link(rel='new', **kwargs)

    def edit(self, **kwargs):
        return self.link(rel='edit', **kwargs)

    def index(self, name=None, **kwargs):
        return self.action(name=name or self.collection_name,
                           action='index', method='GET', **kwargs)

    def show(self, name=None, **kwargs):
        return self.action(name=name or self.resource_name,
                           action='show', method='GET', **kwargs)

    def create(self, **kwargs):
        return self.action(action='create', method='POST', **kwargs)

    def update(self, **kwargs):
        return self.action(action='update', method='PUT', **kwargs)

    def delete(self, **kwargs):
        return self.action(action='delete', method='DELETE', **kwargs)

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        pass


def _kwargs_with_conditions(kwargs, method):
    """Create kwargs wiht a conditions member generated for ht given method"""
    if method and 'conditions' not in kwargs:
        newkwargs = kwargs.copy()
        newkwargs['conditions'] = {'method': method}
        return newkwargs
    else:
        return kwargs


class Mapper(SubMapperParent):
    """Mapper handles URL generation and URL recognition in a web
    application."""

