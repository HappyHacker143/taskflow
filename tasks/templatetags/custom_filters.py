from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Lookup a key in a dictionary."""
    return dictionary.get(key, [])
