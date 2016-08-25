# -*- coding: utf-8 -*-
# Copyright (c) 2015, Webonyx and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, datetime
from frappe.desk.reportview import build_match_conditions
from frappe.utils.data import get_datetime_str
from frappe.model.document import Document
from erpnext.stock.doctype.item.item import Item
from erpnext_biotrack.erpnext_biotrack.doctype.strain import find_strain

class Plant(Document):

	def sync_with_biotrack(self, data):
		warehouse = frappe.get_doc("Warehouse", {"external_id": data.get("room"), "plant_room": 1})

		properties = {
			"strain": find_strain(data.get("strain")),
			"warehouse": warehouse.name,
			"is_mother_plant": int(data.get("mother")),
			"remove_scheduled": int(data.get("removescheduled")),
		}

		if properties["remove_scheduled"]:
			remove_datetime = datetime.datetime.fromtimestamp(int(data.get("removescheduletime")))
			properties["remove_time"] = get_datetime_str(remove_datetime)

			if data.get("removereason"):
				properties["remove_reason"] = data.get("removereason")

		state = int(data.get("state"))
		properties["state"] = "Drying" if state == 1 else ("Cured" if state == 2 else "Growing")

		self.update(properties)
		self.save(ignore_permissions=True)

def get_plant_list(doctype, txt, searchfield, start, page_len, filters):
	fields = ["name", "strain"]
	match_conditions = build_match_conditions("Plant")
	match_conditions = "and {}".format(match_conditions) if match_conditions else ""

	return frappe.db.sql("""select %s from `tabPlant` where docstatus < 2
		and (%s like %s or strain like %s)
		{match_conditions}
		order by
		case when name like %s then 0 else 1 end,
		case when strain like %s then 0 else 1 end,
		name, strain limit %s, %s""".format(match_conditions=match_conditions) %
		(", ".join(fields), searchfield, "%s", "%s", "%s", "%s", "%s", "%s"),
		("%%%s%%" % txt, "%%%s%%" % txt, "%%%s%%" % txt, "%%%s%%" % txt, start, page_len))