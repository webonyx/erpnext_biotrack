from __future__ import unicode_literals
from frappe import _

def get_data():
    return [
        {
            "module_name": "Traceability",
            "label": _("Traceability"),
            "color": "green",
            "icon": "fa fa-leaf",
            "type": "module",
            "hidden": 1
        },
    ]
