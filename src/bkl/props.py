#
#  This file is part of Bakefile (http://www.bakefile.org)
#
#  Copyright (C) 2009-2011 Vaclav Slavik
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to
#  deal in the Software without restriction, including without limitation the
#  rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
#  sell copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#  FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
#  IN THE SOFTWARE.
#

"""
Keep track of properties for extensions or model parts.

Also define standard, always available, properties.
"""

import expr, api, utils
from vartypes import IdType, EnumType, ListType
from api import Property

def std_target_props():
    """Creates list of all standard target properties."""
    return [
        Property("id",
                 type=IdType(),
                 default=lambda t: expr.LiteralExpr(t.name),
                 readonly=True,
                 doc="Target's unique name (ID)."),

        Property("deps",
                 type=ListType(IdType()),
                 default=[],
                 doc="Target's dependencies (list of IDs)."),
        ]


def std_module_props():
    """Creates list of all standard module properties."""
    toolsets_enum_type = EnumType(api.Toolset.all_names())

    return [
        Property("toolsets",
                 type=ListType(toolsets_enum_type),
                 default=[],
                 doc="List of toolsets to generate makefiles/projects for."),
        ]


def std_project_props():
    """Creates list of all standard project properties."""
    toolsets_enum_type = EnumType(api.Toolset.all_names())

    return [
        Property("toolset",
                 type=toolsets_enum_type,
                 default=expr.UndeterminedExpr(),
                 readonly=True,
                 doc="The toolset makefiles or projects are being generated for. "
                     "This property is set by Bakefile and can be used for performing "
                     "toolset-specific tasks or modifications."
                 ),
        ]


class PropertiesDict(utils.OrderedDict):
    """Dictionary of properties, keyed by their names."""
    def add(self, prop):
        self[prop.name] = prop

def _fill_prop_dict(props):
    d = PropertiesDict()
    for p in props:
        d.add(p)
    return d


class PropertiesRegistry(object):
    """
    Registry of existing properties.
    """
    def __init__(self):
        self.all_targets = None
        self.modules = None
        self.project = None
        self.target_types = {}

    def get_project_prop(self, name):
        """
        Returns property *name* on module level if such property exists, or
        :const:`None` otherwise.
        """
        if self.project is None:
            self._init_project_props()
        return self.project.get(name, None)

    def get_module_prop(self, name):
        """
        Returns property *name* on module level if such property exists, or
        :const:`None` otherwise.
        """
        if self.modules is None:
            self._init_module_props()
        return self.modules.get(name, None)

    def get_target_prop(self, target_type, name):
        """
        Returns property *name* on target level for targets of type *target_type*
        if such property exists, or :const:`None` otherwise.
        """
        if self.all_targets is None or target_type not in self.target_types:
            self._init_target_props(target_type)
        if name in self.all_targets:
            return self.all_targets[name]
        else:
            return self.target_types[target_type].get(name, None)
    
    def enum_project_props(self):
        if self.project is None:
            self._init_project_props()
        for p in self.project.itervalues():
            yield p

    def enum_module_props(self):
        if self.modules is None:
            self._init_module_props()
        for p in self.modules.itervalues():
            yield p

    def enum_target_props(self, target_type):
        if self.all_targets is None or target_type not in self.target_types:
            self._init_target_props(target_type)
        for p in self.target_types[target_type].itervalues():
            yield p
        for p in self.all_targets.itervalues():
            yield p

    def _init_project_props(self):
        if self.project is not None:
            return
        self.project = _fill_prop_dict(std_project_props())
        for toolset in api.Toolset.all():
            for p in toolset.all_properties("properties_project"):
                p.toolsets = [toolset.name]
                p.scope = api.Property.SCOPE_PROJECT
                self.project.add(p)

    def _init_module_props(self):
        if self.modules is not None:
            return
        self.modules = _fill_prop_dict(std_module_props())
        for toolset in api.Toolset.all():
            for p in toolset.all_properties("properties_module"):
                p.toolsets = [toolset.name]
                p.scope = api.Property.SCOPE_MODULE
                self.modules.add(p)

    def _init_target_props(self, target_type):
        if self.all_targets is None:
            self.all_targets = _fill_prop_dict(std_target_props())
            for toolset in api.Toolset.all():
                for p in toolset.all_properties("properties_target"):
                    p.toolsets = [toolset.name]
                    p.scope = api.Property.SCOPE_TARGET
                    self.all_targets.add(p)
        if target_type not in self.target_types:
            props = _fill_prop_dict(target_type.all_properties())
            for toolset in api.Toolset.all():
                for p in toolset.all_properties("properties_%s" % target_type):
                    p.toolsets = [toolset.name]
                    p.scope = target_type
                    props.add(p)
            self.target_types[target_type] = props


registry = PropertiesRegistry()

get_project_prop = registry.get_project_prop
get_module_prop = registry.get_module_prop
get_target_prop = registry.get_target_prop

enum_project_props = registry.enum_project_props
enum_module_props = registry.enum_module_props
enum_target_props = registry.enum_target_props