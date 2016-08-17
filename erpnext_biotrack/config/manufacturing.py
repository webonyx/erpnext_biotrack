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
					"label": "Plants",
				},
				{
					"type": "doctype",
					"name": "Strain",
					"label": "Strains",
				},
				{
					"type": "doctype",
					"name": "Supplier",
					"label": "QA Labs",
					"filters": {"supplier_type": _("Lab & Scientific")},
					"hide_count": True
				},
			]
		}
	]
