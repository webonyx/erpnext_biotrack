from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"label": _("Stock Transactions"),
			"items": [
				{
					"type": "doctype",
					"name": "Stock Type",
					"description": _("BioTrack Inventory Type"),
				},
				{
					"type": "doctype",
					"name": "Stock Status",
				},
				{
					"type": "doctype",
					"name": "Strain",
				}
			]
		}
	]
