from __future__ import unicode_literals
from frappe import _


def get_data():
    return [
        {
            "label": _("Cultivation"),
            "items": [
				{
                    "type": "doctype",
                    "name": "Plant",
                },
				{
                    "type": "doctype",
                    "name": "Plant Entry",
                },
                {
                    "type": "doctype",
                    "name": "Plant Room",
                },
                {
                    "type": "doctype",
                    "name": "Strain",
                }
            ]
        },
		{
            "label": _("Inventory"),
            "items": [
                {
                    "type": "doctype",
                    "name": "Item",
                },
				{
                    "type": "doctype",
                    "name": "Item Group",
                },
				{
                    "type": "doctype",
                    "name": "Warehouse",
                }
            ]
        },
		{
			"label": _("Integrations"),
			"items": [
				{
					"type": "doctype",
					"name": "BioTrack Settings",
					"label": "BioTrackTHC Settings",
				}
			]
		}
    ]
