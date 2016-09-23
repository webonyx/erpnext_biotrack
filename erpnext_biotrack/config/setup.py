from __future__ import unicode_literals
from frappe import _


def get_data():
    return [
        {
            "label": _("Integrations"),
            "icon": "icon-star",
            "items": [
                {
                    "type": "doctype",
                    "name": "BioTrack Settings",
                    "label": "WA State Compliance Settings",
                },
                {
                    "type": "doctype",
                    "name": "BioTrack Log",
                    "label": "WA State Compliance Syncing Logs",
                }
            ]
        }
    ]
