from datetime import datetime, date
from decimal import Decimal

def serialize_value(value):
    from django.db.models import Model

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, Decimal):
        return str(value)

    if isinstance(value, Model):
        return str(value)  # ou value.pk

    return value


def serialize_dict(data):
    return {
        key: serialize_value(value)
        for key, value in data.items()
    }