from django import template


register = template.Library()

@register.simple_tag(name="rfq_line_for")
def rfq_line_for(lines, item_id, vendor_id):
    """
    Get RFQVendorLine from dict keyed by (item_id, vendor_id).
    Usage:
      {% rfq_line_for lines item.id vendor.id as ln %}
    """
    if not lines:
        return None
    try:
        return lines.get((int(item_id), int(vendor_id)))
    except Exception:
        return None


@register.filter(name="rfq_line")
def rfq_line(lines, key: str):
    """
    Get RFQVendorLine from dict keyed by (item_id, vendor_id).
    Usage: {{ lines|rfq_line:"<item_id>,<vendor_id>" }}
    """
    if not lines or not key:
        return None
    try:
        a, b = key.split(",", 1)
        item_id = int(a.strip())
        vendor_id = int(b.strip())
    except Exception:
        return None
    return lines.get((item_id, vendor_id))


@register.filter(name="dict_get")
def dict_get(mapping, key):
    if not mapping or key in (None, ''):
        return None
    try:
        return mapping.get(key)
    except Exception:
        return None

