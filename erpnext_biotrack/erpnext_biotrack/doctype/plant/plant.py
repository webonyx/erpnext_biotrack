# -*- coding: utf-8 -*-
# Copyright (c) 2015, Webonyx and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, datetime
from erpnext_biotrack.biotrackthc import call as biotrackthc_call
from erpnext_biotrack.item_utils import get_item_values
from frappe.desk.reportview import build_match_conditions
from frappe.utils.data import get_datetime_str, DATE_FORMAT, cint, now
from frappe.model.document import Document
from erpnext_biotrack.erpnext_biotrack.doctype.strain import find_strain
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

removal_reasons = {
	0: 'Other',
	1: 'Waste',
	2: 'Unhealthy or Died',
	3: 'Infestation',
	4: 'Product Return',
	5: 'Mistake',
	6: 'Spoilage',
	7: 'Quality Control'
}


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
		if not frappe.flags.force_sync or False and self.get("transaction_id") == data.get("transactionid"):
			frappe.db.set_value("Plant", self.name, "last_sync", now(), update_modified=False)
			return

		warehouse = frappe.get_doc("Warehouse", {"external_id": data.get("room"), "warehouse_type": 'Plant Room'})
		properties = {
			"strain": find_strain(data.get("strain")),
			"warehouse": warehouse.name,
			"is_mother_plant": cint(data.get("mother")),
			"remove_scheduled": cint(data.get("removescheduled")),
			"transaction_id": cint(data.get("transactionid")),
			"last_sync": now(),
		}

		item_values = get_item_values(data.get("parentid"), ["name", "item_group"])
		if item_values:
			properties["source"], properties["item_group"] = item_values

		if not self.get("birthdate"):
			if isinstance(self.get("creation"), basestring):
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

	@Document.whitelist
	def undo(self):
		biotrackthc_call("plant_new_undo", {
			"barcodeid": [self.name],
		})

		# Restore Item source balance
		item = frappe.get_doc("Item", self.get("source"))
		make_stock_entry(item_code=item.name, target=item.default_warehouse, qty=1)
		self.delete()

	@Document.whitelist
	def destroy_schedule(self, reason, reason_txt=None, override=None):
		data = {
			'barcodeid': [self.name],
			'reason_extended': removal_reasons.keys()[removal_reasons.values().index(reason)],
			'reason': reason_txt
		}

		if self.remove_scheduled and not override:
			frappe.throw(
				"Plant <strong>{}</strong> has already been scheduled for destruction. Check <strong>`Reset Scheduled time`</strong> to override.".format(
					self.name))

		if override:
			data['override'] = 1

		biotrackthc_call("plant_destroy_schedule", data)

		self.remove_scheduled = 1
		self.remove_reason = reason_txt or reason
		self.remove_time = now()
		self.save()

	@Document.whitelist
	def destroy_schedule_undo(self):
		biotrackthc_call("plant_destroy_schedule_undo", {'barcodeid': [self.name]})
		self.remove_scheduled = 0
		self.remove_reason = None
		self.remove_time = None
		self.save()

	@Document.whitelist
	def harvest_schedule(self):
		biotrackthc_call("plant_harvest_schedule", {'barcodeid': [self.name]})
		self.harvest_scheduled = 1
		self.harvest_schedule_time = now()
		self.save()

	@Document.whitelist
	def harvest_schedule_undo(self):
		biotrackthc_call("plant_harvest_schedule_undo", {'barcodeid': [self.name]})
		self.harvest_scheduled = 0
		self.harvest_schedule_time = None
		self.save()

	@Document.whitelist
	def destroy(self):
		biotrackthc_call("plant_destroy", {'barcodeid': [self.name]})
		self.delete()


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
