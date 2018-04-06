import sys
import collections

import django
from django import template
from django.conf import settings
from django.template.defaulttags import url
from django.template import Node, TemplateSyntaxError


PY3 = sys.version_info[0] == 3
if PY3:
    from django.utils import six

from treemenus.models import Menu, MenuItem
from treemenus.config import APP_LABEL
from treemenus.utils import get_menu_dict


register = template.Library()


@register.simple_tag
def get_treemenus_static_prefix():
    if django.VERSION >= (1, 3):
        from django.templatetags.static import PrefixNode
        return PrefixNode.handle_simple("STATIC_URL") + 'treemenus/img'
    else:
        from django.contrib.admin.templatetags.adminmedia import admin_media_prefix
        return admin_media_prefix() + 'img/admin/'


@register.simple_tag
def get_menu_variable(menu_name):
    menu = collections.defaultdict(dict)
    try:
        menu = get_menu_dict(menu_name)
    except Menu.DoesNotExist as e:
        if settings.DEBUG:
            raise e
        else:
            return menu
    return menu
    
    
def show_menu(context, menu_name, menu_type=None):
    try:
        menu = get_menu_dict(menu_name)
    except Menu.DoesNotExist as e:
        if settings.DEBUG:
            raise e
        else:
            return context
    context['menu'] = menu
    if menu_type:
        context['menu_type'] = menu_type
    return context
register.inclusion_tag('%s/menu.html' % APP_LABEL, takes_context=True)(show_menu)


def show_menu_variable(context, menu_variable, menu_type=None):
    context['menu'] = menu_variable
    if menu_type:
        context['menu_type'] = menu_type
    return context
register.inclusion_tag('%s/menu.html' % APP_LABEL, takes_context=True)(show_menu_variable)


def show_menu_item(context, menu_item):
    if not isinstance(menu_item['value'], MenuItem):
        error_message = 'Given argument must be a MenuItem object.'
        raise template.TemplateSyntaxError(error_message)

    context['menu_item'] = menu_item
    return context
register.inclusion_tag('%s/menu_item.html' % APP_LABEL, takes_context=True)(show_menu_item)


class ReverseNamedURLNode(Node):
    def __init__(self, named_url, parser):
        self.named_url = named_url
        self.parser = parser

    def render(self, context):
        from django.template import TOKEN_BLOCK, Token

        resolved_named_url = self.named_url.resolve(context)
        if django.VERSION >= (1, 3):
            contents = 'url "%s"' % resolved_named_url
        else:
            contents = 'url %s' % resolved_named_url

        urlNode = url(self.parser, Token(token_type=TOKEN_BLOCK, contents=contents))
        return urlNode.render(context)


def reverse_named_url(parser, token):
    bits = token.contents.split(' ', 2)
    if len(bits) != 2:
        raise TemplateSyntaxError("'%s' takes only one argument"
                                  " (named url)" % bits[0])
    named_url = parser.compile_filter(bits[1])

    return ReverseNamedURLNode(named_url, parser)
reverse_named_url = register.tag(reverse_named_url)
