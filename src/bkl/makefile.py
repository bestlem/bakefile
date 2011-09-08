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
Foundation code for makefile-based toolsets.

All makefile-based toolsets should derive from MakefileToolset defined
in this module.
"""

import types
import os.path

import io
import expr
from bkl.api import Extension, Toolset, Property
from bkl.vartypes import PathType


class MakefileFormatter(Extension):
    """
    MakefileFormatter extensions are used to format makefiles content
    (i.e. targets and their commands) in the particular makefiles format.

    This includes things such as expressing conditional content, referencing
    variables and so on.

    Note that formatters do *not* handle platform- or compiler-specific things,
    e.g. path separators or compiler invocation. There are done by
    :class:`bkl.expr.Formatter` and :class:`bkl.api.FileCompiler` classes.

    This base class implements methods that are common for most make variants;
    derived classes can override them and they must implement the rest.
    """

    @staticmethod
    def comment(text):
        """
        Returns given (possibly multi-line) string formatted as a comment.

        :param text: text of the comment
        """
        return "\n".join("# %s" % s for s in text.split("\n"))


    @staticmethod
    def var_reference(var):
        """
        Returns string with code for referencing a variable.

        For most `make` implementations out there, `var_reference("FOO")`
        returns `"$(FOO)"`.

        :param var: string with name of the variable
        """
        return "$(%s)" % var


    @staticmethod
    def var_definition(var, value):
        """
        Returns string with definition of a variable value, typically
        `var = value`.

        :param var:   variable being defined
        :param value: value of the variable; this string is already formatted
                      to be in make's syntax (e.g. using var_reference()) and
                      may be multi-line
        """
        return "%s = %s" % (var, " \\\n\t".join(value.split("\n")))


    @staticmethod
    def target(name, deps, commands):
        """
        Returns string with target definition.

        :param name:     Name of the target.
        :param deps:     List of its dependencies. Items are strings
                         corresponding to some target's name (may be expressions
                         that reference a variable, in that case the string
                         must already be processed with :meth:`var_reference`).
                         May be empty.
        :param commands: List of commands to execute to build the target; they
                         are already formatted to be in make's syntax and each
                         command in the list is single-line shell command.
        """
        out = "%s:" % name
        if deps:
            out += " "
            out += " ".join(deps)
        if commands:
            for c in commands:
                out += "\n\t%s" % c
        out += "\n\n"
        return out



class _MakefileExprFormatter(expr.Formatter):

    def __init__(self, makefile_formatter, paths_info):
        super(_MakefileExprFormatter, self).__init__(paths_info)
        self.makefile_formatter = makefile_formatter

    def reference(self, e):
        return self.makefile_formatter.var_reference(e.var)



class MakefileToolset(Toolset):
    """
    Base class for makefile-based toolsets.
    """

    #: :class:`MakefileFormatter`-derived class for this toolset.
    Formatter = None

    #: Default filename from output makefile.
    default_makefile = None

    properties = [
            Property("makefile",
                     type=PathType(),
                     # FIXME: assign default value: if-expression evaluating
                     #        to every possibility
                     doc="Name of output file for module's makefile."),
    ]


    def generate(self, project):
        for m in project.modules:
            self._gen_makefile(m)


    def _gen_makefile(self, module):
        assert self.default_makefile is not None

        # FIXME: require the value, use get_variable_value(), set the default
        #        value instead
        output_var = module.get_variable("makefile")
        if output_var is None:
            # FIXME: instead of this, the default is supposed to be relative
            #        to @srcdir
            output = os.path.join(os.path.dirname(module.source_file),
                                  self.default_makefile)
        else:
            output = output_var.value.as_py()

        paths_info = expr.PathAnchors(
                dirsep="/", # FIXME - format-configurable
                outpath=os.path.dirname(output),
                # FIXME: topdir should be constant, this is akin to @srcdir
                top_srcpath=os.path.dirname(module.source_file)
            )

        expr_fmt = _MakefileExprFormatter(self.Formatter, paths_info)

        f = io.OutputFile(output)

        for v in module.variables:
            pass
        for t in module.targets.itervalues():
            graph = t.type.get_build_subgraph(self, t)

            for node in graph:
                if node.name:
                    out = node.name
                else:
                    # FIXME: handle multi-output nodes too
                    assert len(node.outputs) == 1
                    out = node.outputs[0]
                deps = [expr_fmt.format(i) for i in node.inputs]
                deps += [expr_fmt.format(module.get_target(id).get_variable_value("id")) for id in t.get_variable_value("deps").as_py()]
                text = self.Formatter.target(
                        name=expr_fmt.format(out),
                        deps=deps,
                        commands=[expr_fmt.format(c) for c in node.commands])
                f.write(text)

        f.commit()