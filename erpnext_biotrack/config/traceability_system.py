from __future__ import unicode_literals
from frappe import _


def get_data():
    return [
        {
            "label": _("Traceability System"),
            "items": [
                {
                    "type": "doctype",
                    "name": "Plant",
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
			"label": _("Integrations"),
			"items": [
				{
					"type": "doctype",
					"name": "BioTrack Settings",
					"label": "BioTrackTHC Settings",
				},
				{
					"type": "doctype",
					"name": "BioTrack Log",
					"label": "BioTrackTHC Sync Log",
				}
			]
		}
    ]
