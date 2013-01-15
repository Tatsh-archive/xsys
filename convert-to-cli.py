#!/usr/bin/python

from unparse import Unparser
from ast import *
from pprint import PrettyPrinter
import sys

class replaceXchatCalls(NodeTransformer):
    _remove = [
        'hook_command',
        'hook_print',
        'hook_server',
        'hook_timer',
        'hook_unload',
        'unhook',
        'emit_print',
    ]

    _replace_with_print = [
        'command',
        'prnt',
    ]

    # NOTE Not very context sensitive
    _variables = {}

    NORMAL_RETURN_XCHAT_OFFSET = 4

    def visit_Import(self, node):
        """ Remove *import xchat* statement """

        for alias in node.names:
            if alias.name == 'xchat':
                return None

        return node

    def visit_Assign(self, node):
        """ Remove xchat.get_*() and xchat.find_context() assignments """

        for tnode in node.targets:
            if isinstance(tnode, Name) and isinstance(node.value, Call):
                attr = getattr(node.value, 'func', None)
                if isinstance(attr, Attribute) and getattr(attr.value, 'id', None) == 'xchat':
                        if getattr(self._variables, attr.attr, False) is False:
                            self._variables[attr.attr] = []

                        self._variables[attr.attr].append(tnode.id)
                        #print '%d Removing assignment "%s = xchat.%s()"' % (tnode.lineno, tnode.id, attr.attr)
                        return None
        return node

    def visit_Return(self, node):
        """ Remove/replace all xchat.* return statements """

        if isinstance(node.value, Attribute) and node.value.value.id == 'xchat':
            if node.col_offset == self.NORMAL_RETURN_XCHAT_OFFSET:
                #print '%d Removing "return xchat.%s"' % (node.value.lineno, node.value.attr)
                return None

            #print '%d Replacing "return.%s" with "return"' % (node.value.lineno, node.value.attr)
            return copy_location(Return(value=None), node)
        return node

    def visit_Call(self, node):
        """ Replace xchat.* function calls like *prnt()* and *command()* with regular print """

        func = node.func
        value = getattr(func, 'value', None)
        attr_id = getattr(value, 'id', None)

        if isinstance(func, Attribute) and attr_id == 'xchat':
            if func.attr in self._remove:
                #print '%d Removing "xchat.%s()" call' % (func.lineno, func.attr)
                special_arg = Num(n=0)
                if node.args[1].id.startswith('net'):
                    special_arg = List(elts=[Str(s=''), Str(s='eth0')], ctx=Load())

                arguments = [special_arg, Num(n=0), Num(n=0)]

                return copy_location(Call(func=Name(
                    id=node.args[1].id,
                    ctx=Load()
                ), args=arguments, keywords=[], starargs=None, kwargs=None), node)
            elif func.attr in self._replace_with_print:
                #print '%d Replacing "xchat.%s(\'%s\')" with "print" version' % (func.lineno, func.attr, node.args[0].s)
                return copy_location(Print(
                    dest=None,
                    values=node.args,
                    nl=True
                ), node)
        elif isinstance(func, Attribute) and isinstance(func.value, Name):
            if func.attr in self._replace_with_print:
                for key in self._variables:
                    if func.value.id in self._variables[key]:
                        #print '%d Replacing "%s.some_func()" call with regular print' % (func.lineno, func.value.id)
                        return copy_location(Print(
                            dest=None,
                            values=node.args,
                            nl=True
                        ), node)

        return node

with open('./xsys.py') as f:
    top_node = parse(''.join(f))
    ast = replaceXchatCalls().visit(top_node)
    code = parse(ast)
    Unparser(code, sys.stdout)
    print ''
