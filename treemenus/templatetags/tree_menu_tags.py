import sys
import collections
import copy

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


register = template.Library()


@register.simple_tag
def get_treemenus_static_prefix():
    if django.VERSION >= (1, 3):
        from django.templatetags.static import PrefixNode
        return PrefixNode.handle_simple("STATIC_URL") + 'treemenus/img'
    else:
        from django.contrib.admin.templatetags.adminmedia import admin_media_prefix
        return admin_media_prefix() + 'img/admin/'


def show_menu(context, menu_name, menu_type=None):
    try:
        menu_object = Menu.objects.get(name=menu_name)
        # Fetch menu in single query
        menu_items = MenuItem.objects.filter(menu_id=menu_object.id)\
            .order_by('-level', 'parent_id', 'rank')\
            .select_related('extension')

        # Flag which determines that first level has been processed
        previous_level = -1
        current_level = -1
        menu = collections.defaultdict(dict)
        menu_temp = collections.defaultdict(dict)

        # The whole Menu is created as dictionary in this loop
        for menu_item in menu_items:
            if menu_item.level != 0:
                if current_level != -1 and current_level != menu_item.level and menu_item.level != '0':
                    previous_level = current_level
                    menu_temp = copy.deepcopy(menu)
                    menu = collections.defaultdict(dict)
                current_level = menu_item.level
                if previous_level == -1:
                    if 'children' not in menu[menu_item.parent_id].keys():
                        menu[menu_item.parent_id]['children'] = []
                    child = {"value": menu_item, 'children':[]}
                    menu[menu_item.parent_id]['children'].append(child)
                else:
                    index = menu_item.parent_id
                    if menu_item.level == 1:
                        index = 0
                    menu_temp[menu_item.id]['value'] = menu_item
                    if 'children' not in menu_temp[menu_item.id].keys():
                        menu_temp[menu_item.id]['children'] = []
                    if 'children' not in menu[index].keys():
                        menu[index]['children'] = []
                    menu[index]['children'].append(copy.deepcopy(menu_temp[menu_item.id]))

    except Menu.DoesNotExist as e:
        if settings.DEBUG:
            raise e
        else:
            return []

    context['menu'] = menu[0]['children']
    if menu_type:
        context['menu_type'] = menu_type
    return context
register.inclusion_tag('%s/menu.html' % APP_LABEL, takes_context=True)(show_menu)


def show_menu_item(context, menu_item):
    if not isinstance(menu_item, MenuItem):
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
