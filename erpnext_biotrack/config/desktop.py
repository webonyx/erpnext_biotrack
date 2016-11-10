from __future__ import unicode_literals
from frappe import _

def get_data():
    return [
        {
            "module_name": "Traceability System",
            "label": _("Traceability System"),
            "color": "green",
            "icon": "icon-leaf",
            "type": "module",
            "system_manager": 1,
            "hidden": 1
        },
    ]
