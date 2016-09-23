from __future__ import unicode_literals
from frappe import _


def get_data():
    return [
        {
            "label": _("Production"),
            "items": [
                {
                    "type": "doctype",
                    "name": "Plant",
                },
                {
                    "type": "doctype",
                    "name": "Strain",
                }
            ]
        }
    ]
