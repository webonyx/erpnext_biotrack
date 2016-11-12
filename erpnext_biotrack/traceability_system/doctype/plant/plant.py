# -*- coding: utf-8 -*-
# Copyright (c) 2015, Webonyx and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, datetime
from erpnext.stock.utils import get_stock_balance
from erpnext_biotrack.biotrackthc import call as biotrackthc_call
from erpnext_biotrack.biotrackthc.client import BioTrackClientError
from erpnext_biotrack.biotrackthc.inventory_room import get_default_warehouse
from erpnext_biotrack.item_utils import get_item_values, make_item, generate_item_code
from frappe.desk.reportview import build_match_conditions
from frappe.utils.data import get_datetime_str, DATETIME_FORMAT, cint, now, flt, add_to_date
from frappe.model.document import Document
from erpnext_biotrack.erpnext_biotrack.doctype.strain import find_strain
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from frappe.utils.background_jobs import enqueue

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
	def on_submit(self):
		if frappe.flags.in_import or frappe.flags.in_test:
			return

		self.validate_item_balance()
		self.make_stock_entry()

	def on_cancel(self):
		self.make_stock_entry_cancel()

	def on_trash(self):
		# able to delete new Plants
		if self.state == "Growing" or not self.harvest_scheduled:
			return

		if not self.remove_scheduled:
			frappe.throw("Plant can not be deleted directly. Please schedule for destruction first")

		if not self.disabled:
			frappe.throw("Plant can only be deleted once destroyed")

	def validate_item_balance(self):
		# able to delete new Plants
		item = frappe.get_doc("Item", self.get("item_code"))
		qty = get_stock_balance(item.item_code, item.default_warehouse)
		if qty < self.qty:
			frappe.throw("The provided quantity <strong>{0}</strong> exceeds stock balance. "
						 "Stock balance remaining <strong>{1}</strong>".format(self.qty, qty))

	def make_stock_entry(self):
		item = frappe.get_doc("Item", self.get("item_code"))
		ste = make_stock_entry(item_code=item.name, source=item.default_warehouse, qty=1, do_not_save=True)
		ste.plant = self.name
		ste.submit()


	def make_stock_entry_cancel(self):
		name = frappe.db.exists("Stock Entry", {"plant": self.name})
		if name:
			ste = frappe.get_doc("Stock Entry", name)
			ste.cancel()


	def collect_item(self, item_group, qty):
		default_warehouse = get_default_warehouse()
		naming_series = frappe.get_meta("Item").get_options("naming_series") or "ITEM-"

		return make_item(properties={
			"item_name": item_group.item_group_name,
			"item_code": generate_item_code(naming_series),
			"item_group": item_group.name,
			"default_warehouse": default_warehouse.name,
			"strain": self.get("strain"),
			"stock_uom": "Gram",
			"is_stock_item": 1,
			"plant": self.name,
		}, qty=qty)


	def delete_related_items(self):
		for item_name in frappe.get_all("Item", {"plant": self.name}):
			item = frappe.get_doc("Item", item_name)
			for name in frappe.get_list("Stock Entry", {"item_code": item.item_code}):
				ste = frappe.get_doc("Stock Entry", name)
				ste.cancel()
				ste.delete()
			item.delete()

	def biotrack_sync_down(self, data):
		if not (frappe.flags.force_sync or False) and self.get("transaction_id") == data.get("transactionid"):
			frappe.db.set_value("Plant", self.name, "last_sync", now(), update_modified=False)
			return

		plant_room = frappe.get_doc("Plant Room", {"external_id": data.get("room")})
		properties = {
			"strain": find_strain(data.get("strain")),
			"warehouse": plant_room.get("name") if plant_room else "",
			"is_mother_plant": cint(data.get("mother")),
			"remove_scheduled": cint(data.get("removescheduled")),
			"transaction_id": cint(data.get("transactionid")),
			"last_sync": now(),
			"disabled": 0,
		}

		item_values = get_item_values(data.get("parentid"), ["name", "item_group"])
		if item_values:
			properties["source"], properties["item_group"] = item_values

		if not self.get("birthdate"):
			if isinstance(self.get("creation"), basestring):
				properties["birthdate"] = self.get("creation")
			else:
				properties["birthdate"] = self.get("creation").strftime(DATETIME_FORMAT)

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
	def cure(self, flower, other_material=None, waste=None, additional_collection=None):
		if self.disabled:
			frappe.throw("Plant <strong>{}</strong> is not available for harvesting.")

		if self.remove_scheduled:
			frappe.throw("Plant <strong>{}</strong> is currently scheduled for destruction and cannot be harvested.")

		self.dry_weight = flt(self.dry_weight) + flt(flower)
		if self.dry_weight > self.wet_weight:
			frappe.throw(
				"The provided dry weight <strong>{0}</strong> exceeds the previous wet weight <strong>{1}</strong>.".
					format(self.dry_weight, self.wet_weight), title="Error")

		items = []
		frappe.flags.ignore_external_sync = True

		# collect Flower
		item_group = frappe.get_doc("Item Group", {"external_id": 6})
		items.append(self.collect_item(item_group, flower))

		if other_material:
			item_group = frappe.get_doc("Item Group", {"external_id": 9})
			items.append(self.collect_item(item_group, other_material))

		if waste:
			item_group = frappe.get_doc("Item Group", {"external_id": 27})
			items.append(self.collect_item(item_group, waste))


		# Remove from Cultivation
		if not additional_collection or self.dry_weight == self.wet_weight:
			self.disabled = 1

		self.flags.ignore_validate_update_after_submit = True
		self.save()

		# hook
		self.run_method("after_cure", items=items, flower=flower, other_material=other_material, waste=waste, additional_collection=additional_collection)

		return {"items": items}

	@Document.whitelist
	def cure_undo(self):
		if not self.disabled:
			frappe.throw("Invalid action")

		self.run_method("before_cure_undo")

		# self.delete_related_items()

		self.disabled = 0
		self.flags.ignore_validate_update_after_submit = True
		self.save()

	@Document.whitelist
	def harvest(self, flower, other_material=None, waste=None):
		if self.disabled:
			frappe.throw("Plant <strong>{}</strong> is not available for harvesting.")

		if self.remove_scheduled:
			frappe.throw("Plant <strong>{}</strong> is currently scheduled for destruction and cannot be harvested.")

		items = []
		frappe.flags.ignore_external_sync = True
		if other_material:
			item_group = frappe.get_doc("Item Group", {"external_id": 9})
			items.append(self.collect_item(item_group, other_material))

		if waste:
			item_group = frappe.get_doc("Item Group", {"external_id": 27})
			items.append(self.collect_item(item_group, waste))

		self.wet_weight = flower
		self.state = "Drying"

		self.flags.ignore_validate_update_after_submit = True
		self.save()

		self.run_method("after_harvest", items=items, flower=flower, other_material=other_material, waste=waste)

		return {"items": items}

	@Document.whitelist
	def harvest_undo(self):
		if self.state != "Drying":
			frappe.throw("Invalid action")

		self.run_method("before_harvest_undo")

		self.delete_related_items()

		self.wet_weight = 0
		self.dry_weight = 0
		self.state = "Growing"

		self.flags.ignore_validate_update_after_submit = True
		self.save()

	@Document.whitelist
	def destroy_schedule(self, reason, reason_txt=None, override=None):
		if self.remove_scheduled and not override:
			frappe.throw(
				"Plant <strong>{}</strong> has already been scheduled for destruction. Check <strong>`Reset Scheduled time`</strong> to reschedule.".format(
					self.name))

		reason_key = removal_reasons.keys()[removal_reasons.values().index(reason)]
		self.run_method("before_destroy_schedule", reason_key=reason_key, reason=reason_txt, override=override)

		self.remove_scheduled = 1
		self.remove_reason = reason_txt or reason
		self.remove_time = now()
		self.flags.ignore_validate_update_after_submit = True
		self.save()

	@Document.whitelist
	def destroy_schedule_undo(self):
		if not self.remove_scheduled:
			return

		self.run_method("before_destroy_schedule_undo")
		self.flags.ignore_validate_update_after_submit = True
		self.remove_scheduled = 0
		self.remove_reason = None
		self.remove_time = None
		self.save()

	@Document.whitelist
	def harvest_schedule(self):
		if self.harvest_scheduled:
			frappe.throw("Plant <strong>{}</strong> has been scheduled for harvesting.".format(self.name))

		self.run_method("before_harvest_schedule")
		self.harvest_scheduled = 1
		self.harvest_schedule_time = now()

		self.flags.ignore_validate_update_after_submit = True
		self.save()

	@Document.whitelist
	def harvest_schedule_undo(self):
		if not self.harvest_scheduled:
			frappe.throw("Plant <strong>{}</strong> was not in scheduled state.".format(self.name))

		if self.state == "Drying":
			frappe.throw("Plant <strong>{}</strong> has already on harvesting process.".format(self.name))

		self.run_method("before_harvest_schedule_undo")

		self.harvest_scheduled = 0
		self.harvest_schedule_time = None

		self.flags.ignore_validate_update_after_submit = True
		self.save()

	@Document.whitelist
	def convert_to_inventory(self):
		# items = [self.name]
		# res = biotrackthc_call("plant_convert_to_inventory", {'barcodeid': [self.name]})
		# defaukt_warehouse = get_default_warehouse()
		# item_group = frappe.get_doc("Item Group", {"external_id": 12})  # Mature Plant
		# qty = 1
		#
		# for barcode in items:
		# 	make_item(barcode=barcode, properties={
		# 		"item_group": item_group.name,
		# 		"default_warehouse": defaukt_warehouse.name,
		# 		"strain": self.strain,
		# 		"is_stock_item": 1,
		# 		"actual_qty": qty,
		# 		"plant": self.name,
		# 		"parent_item": self.item_code,
		# 	}, qty=qty)
		# self.transaction_id = res.get("transactionid")

		# destroy plant as well
		self.run_method('before_convert_to_inventory')
		self.remove_scheduled = 1
		self.disabled = 1
		self.save()

		self.run_method('after_convert_to_inventory')

	@Document.whitelist
	def destroy(self):
		biotrackthc_call("plant_destroy", {'barcodeid': [self.name]})
		self.delete()


@frappe.whitelist()
def harvest_cure_undo(name, items, action, transaction_id):
	"""Alias to harvest_cure_undo method to avoid check_if_latest exception"""
	plant = frappe.get_doc("Plant", name)

	import json
	try:
		items = json.loads(items)
	except ValueError:
		items = []

	return plant.harvest_cure_undo(items, action, transaction_id)


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


def bulk_clone(name):
	source_plant = frappe.get_doc("Plant", name)

	if source_plant.qty > 1:
		warehouse = frappe.get_doc("Warehouse", source_plant.get("warehouse"))
		location = frappe.get_value("BioTrack Settings", None, "location")
		remaining_qty = source_plant.qty - 1

		result = biotrackthc_call("plant_new", {
			"room": warehouse.external_id,
			"quantity": remaining_qty,
			"strain": source_plant.strain,
			"source": source_plant.item_code,
			"mother": cint(source_plant.get("is_mother")),
			"location": location
		})

		for barcode in result.get("barcode_id"):
			plant = frappe.new_doc("Plant")
			plant.update({
				"barcode": barcode,
				"item_group": source_plant.item_group,
				"source": source_plant.item_code,
				"strain": source_plant.strain,
				"warehouse": source_plant.warehouse,
				"state": source_plant.state,
				"birthdate": now(),
			})

			plant.save()

		# save directly with sql to avoid mistimestamp check
		frappe.db.set_value("Plant", source_plant.name, "qty", 1, update_modified=False)
		frappe.publish_realtime("list_update", {"doctype": "Plant"})


def destroy_scheduled_plants():
	"""Destroy expired Plants"""
	date = add_to_date(now(), days=-3)
	for name in frappe.get_list("Plant",
								[["disabled", "=", 0], ["remove_scheduled", "=", 1], ["remove_time", "<", date]]):
		plant = frappe.get_doc("Plant", name)
		plant.disabled = 1
		plant.save()
