__author__ = 'stevet'
import operator

import maya.cmds as cmds
from util import XYZ


class AttributeQuery(object):
    """
    This is a query-generation helper class.  You can use it to create (simple) attribute value tests inside a query
    like `where` or `where_not` that takes a callable predicate.  For example:

        cameras().where(item.orthographic == True))

    will find all the scene camera with their 'orthographic' attribute set True, while

        meshes().parents.where(item.ty > 0)

    will find all mesh parent transforms whose translate Y attribute is larger than zero.


    The 'item' keywords stands for each value passing through the query.  The attribute value will be resolved when
    the query is evaluated (so if you have a typo, you may not notice it at compile time!)  Any item which is evaluated
    and doesn't have the attribute will automatically fail the test: if a shape is mixed in with a collection of
    transforms, for example, it will fail both item.ty > 0 and item.ty < 0 since it has not 'ty' attribute.

    You can use a stricter evaluation to identify queries that produce bad attribute checks.  If you create the item
    separately and set it's "strict" property to true, it will except when it can't find the attribute:

        is_ortho = item.orthographic == True
        is_ortho.strict = True

        meshes().where(is_ortho)

    will raise a RuntimeException when evaluated, since meshes don't have an `orthographic` attribute.

    If the attribute is compound with XYZ values (such as translate, rotate or scale), the query will automatically
    Maya's annoying default behavior of returning these values as nested lists:

        cmds.getAttr('pCube1.t')
        # Result: [(0,0,0)]

    an item query will instead see the result as (0,0,0), which means you can write:

        some_query.where(item.t == (0,0,0) )

    """
    # these attribs are return as tuples-in-lists by getAttr, so we unpack them
    UNPACK_MULT = ('t', 'translate', 'r', 'rotate', 's', 'scale', 'rp', 'rotatePivot', 'sp', 'scalePivot')

    def __init__(self, attribName, operator=None, comp=None, strict=False):
        self.attrib = attribName
        if self.attrib[0] == ".":
            self.attrib = attribName[1:]
        self.comp = comp
        self.operator = operator
        self.strict = strict
        self.unpack = self.attrib in self.UNPACK_MULT

    def __repr__(self):
        lookup = {
            operator.eq: "==",
            operator.ge: ">=",
            operator.gt: ">",
            operator.le: "<=",
            operator.lt: "<",
            operator.ne: "!=",
            operator.rshift: None,
            None: '?'
        }
        if lookup.get(self.operator):
            return "{attribute: %s %s %s}" % (self.attrib, lookup[self.operator], self.comp)
        else:
            return "%s({attribute: %s})" % (str(self.comp), self.attrib)

    def eval(self, maya_obj):
        try:
            value = cmds.getAttr("{}.{}".format(maya_obj, self.attrib))
            if self.unpack:
                value = XYZ(*value[0])
            if self.operator != operator.rshift:
                return self.operator(value, self.comp)
            else:
                return self.comp(value)
        except:
            if self.strict:
                raise
            return False

    def __eq__(self, other):
        return AttributeQuery(self.attrib, operator=operator.eq, comp=other)

    def __ne__(self, other):
        return AttributeQuery(self.attrib, operator=operator.ne, comp=other)

    def __gt__(self, other):
        return AttributeQuery(self.attrib, operator=operator.gt, comp=other)

    def __ge__(self, other):
        return AttributeQuery(self.attrib, operator=operator.ge, comp=other)

    def __lt__(self, other):
        return AttributeQuery(self.attrib, operator=operator.lt, comp=other)

    def __le__(self, other):
        return AttributeQuery(self.attrib, operator=operator.le, comp=other)

    def __rshift__(self, other):
        return AttributeQuery(self.attrib, operator=operator.rshift, comp=other)

    def __call__(self, maya_obj):
        return self.eval(maya_obj)


def attribute_factory(*args, **kwargs):
    return AttributeQuery(args[1])


class ItemMeta(type):
    def __new__(cls, name, bases, dct):
        result = type.__new__(cls, name, bases, dct)
        setattr(result.__class__, '__getattr__', attribute_factory)
        return result


class item(object):
    """
    Proxies for attribute queries against maya objects
    """
    __metaclass__ = ItemMeta
