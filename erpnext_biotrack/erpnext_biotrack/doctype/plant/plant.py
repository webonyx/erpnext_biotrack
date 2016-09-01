# -*- coding: utf-8 -*-
# Copyright (c) 2015, Webonyx and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, datetime
from erpnext_biotrack.biotrackthc import call as biotrackthc_call
from frappe.desk.reportview import build_match_conditions
from frappe.utils.data import get_datetime_str, DATE_FORMAT, cint
from frappe.model.document import Document
from erpnext_biotrack.erpnext_biotrack.doctype.strain import find_strain
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

class Plant(Document):
	def before_insert(self):
		self.biotrack_sync_up()

	def after_insert(self):
		if frappe.flags.in_import or frappe.flags.in_test:
			return

		source_item = frappe.get_doc("Item", self.get("source"))
		make_stock_entry(item_code=source_item.name, source=source_item.default_warehouse, qty=1)

	def biotrack_sync_up(self):
		if frappe.flags.in_import or frappe.flags.in_test:
			return

		warehouse = frappe.get_doc("Warehouse", self.get("warehouse"))
		location = frappe.get_value("BioTrack Settings", None, "location")

		result = biotrackthc_call("plant_new", {
			"room": warehouse.external_id,
			"quantity": 1,
			"strain": self.get("strain"),
			"source": self.get("source"),
			"mother": cint(self.get("is_mother")),
			"location": location
		})

		self.set("barcode", result.get("barcode_id")[0])

	def biotrack_sync_down(self, data):
		if self.get("transaction_id") == data.get("transactionid"):
			return

		warehouse = frappe.get_doc("Warehouse", {"external_id": data.get("room"), "warehouse_type": 'Plant Room'})


		properties = {
			"strain": find_strain(data.get("strain")),
			"warehouse": warehouse.name,
			"is_mother_plant": cint(data.get("mother")),
			"remove_scheduled": cint(data.get("removescheduled")),
			"transaction_id": cint(data.get("transactionid")),
		}

		if frappe.db.exists("Item", {"barcode": data.get("parentid")}):
			source = frappe.get_doc("Item", {"barcode": data.get("parentid")})
			properties["source"] = source.name
			properties["item_group"] = source.item_group
		else:
			print "skip %s" % data.get("parentid")

		if not self.get("birthdate"):
			if isinstance(self.get("creation"), basestring) :
				properties["birthdate"] = self.get("creation").split(" ")[0]
			else:
				properties["birthdate"] = self.get("creation").strftime(DATE_FORMAT)

		if properties["remove_scheduled"]:
			remove_datetime = datetime.datetime.fromtimestamp(cint(data.get("removescheduletime")))
			properties["remove_time"] = get_datetime_str(remove_datetime)

			if data.get("removereason"):
				properties["remove_reason"] = data.get("removereason")

		state = int(data.get("state"))
		properties["state"] = "Drying" if state == 1 else ("Cured" if state == 2 else "Growing")

		self.update(properties)
		self.flags.ignore_mandatory = True
		self.save(ignore_permissions=True)

@frappe.whitelist()
def plant_new_undo(name):
	doc = frappe.get_doc("Plant", name)
	biotrackthc_call("plant_new_undo", {
		"barcodeid": [doc.name],
	})

	# Restore Item source balance
	item = frappe.get_doc("Item", doc.get("source"))
	make_stock_entry(item_code=item.name, target=item.default_warehouse, qty=1)
	doc.delete()

	return {"ok": 1}

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