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
					"name": "Biotrack Settings",
					"label": "BioTrack Settings",
					"description": _("Connect BioTrack with ERPNext"),
				},
				{
					"type": "doctype",
					"name": "Biotrack Log",
					"label": "BioTrack Log",
				}
			]
		}
	]
