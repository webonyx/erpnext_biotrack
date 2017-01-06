# -*- coding: utf-8 -*-
# Copyright (c) 2015, Webonyx and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import json
import frappe
from frappe import _
from erpnext.stock.utils import get_stock_balance
from erpnext_biotrack.biotrackthc import call as biotrackthc_call
from erpnext_biotrack.biotrackthc.inventory_room import get_default_warehouse
from erpnext_biotrack.item_utils import make_item, generate_item_code
from frappe.desk.reportview import build_match_conditions
from frappe.model.delete_doc import delete_from_table
from frappe.utils import call_hook_method
from frappe.utils.data import cint, now, flt, add_to_date
from frappe.model.document import Document
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
	def validate(self):
		if frappe.flags.in_import:
			return

		if (self.item_code and self.source_plant) or (not self.item_code and not self.source_plant):
			frappe.throw(_('Either Source Plant or Source Item is required.'))

	def before_submit(self):
		if frappe.flags.in_import or self.flags.in_bulk:
			return

		if self.item_code:
			self.validate_item_balance()

		# bulk add
		if self.qty > 1 and self.brother_plant is None:
			self.flags.bulk_add = True
			self.flags.bulk_plants = []

			for i in xrange(self.qty - 1):
				plant = frappe.copy_doc(self)
				plant.qty = 1
				plant.brother_plant = self.name
				plant.flags.in_bulk = True
				plant.save()
				self.flags.bulk_plants.append(plant)

	def on_submit(self):
		# root plant
		if self.brother_plant is None:
			if self.item_code:
				frappe.flags.ignore_external_sync = True
				self.make_stock_entry()
				frappe.flags.ignore_external_sync = False

			# Submit brother plants
			for name in frappe.get_list("Plant", {"brother_plant": self.name}):
				doc = frappe.get_doc("Plant", name)
				if doc.docstatus == 0:
					doc.submit()

	def before_cancel(self):
		if self.flags.in_import:
			return

		if self.item_code:
			self.cancel_stock_entry()

	def on_trash(self):
		# able to delete new Plants
		if self.state == "Growing" or not self.harvest_scheduled:
			return

		if not self.destroy_scheduled:
			frappe.throw("Plant can not be deleted directly. Please schedule for destruction first")

		if not self.disabled:
			frappe.throw("Plant can only be deleted once destroyed")

	def validate_item_balance(self):
		# able to delete new Plants
		source_warehouse = self.get_source_warehouse()

		item = frappe.get_doc("Item", self.get("item_code"))
		qty = get_stock_balance(item.item_code, source_warehouse)
		if qty < self.qty:
			frappe.throw("The provided quantity <strong>{0}</strong> exceeds stock balance in warehouse {1}. "
						 "Stock balance remaining <strong>{2}</strong>".format(self.qty, source_warehouse, qty))

	def get_source_warehouse(self):
		source_warehouse = frappe.db.get_single_value("Traceability Settings", "default_source_warehouse")
		if not source_warehouse:
			filters = {
				"item_code": self.item_code,
				"actual_qty": [">", 0]
			}

			source_warehouse = frappe.get_value("Bin", filters=filters, fieldname='warehouse')

			if not source_warehouse:
				frappe.throw(_("Item {0} is not available in any warehouse").format(self.item_code))

		return source_warehouse

	def make_stock_entry(self):
		item = frappe.get_doc("Item", self.get("item_code"))
		ste = make_stock_entry(item_code=item.name, source=self.get_source_warehouse(), qty=self.qty, do_not_save=True)
		ste.plant = self.name
		ste.submit()


	def revert_on_failure(self):
		for name in frappe.get_list("Plant", {"brother_plant": self.name}):
			doc = frappe.get_doc("Plant", name)
			frappe.delete_doc("Plant", doc.name)

		frappe.db.commit()


	def collect_item(self, item_group, qty):
		default_warehouse = get_default_warehouse()

		return make_item(properties={
			"item_name": " ".join([self.get("strain"), item_group.item_group_name]),
			"item_code": generate_item_code(),
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

	def move_to(self, plant_room):
		frappe.db.set_value("Plant", self.name, "plant_room", plant_room.name)

	@Document.whitelist
	def cure(self, flower, other_material=None, waste=None, additional_collection=None):
		if self.disabled:
			frappe.throw("Plant <strong>{}</strong> is not available for harvesting.")

		if self.destroy_scheduled:
			frappe.throw("Plant <strong>{}</strong> is currently scheduled for destruction and cannot be harvested.")

		self.dry_weight = flt(self.dry_weight) + flt(flower)
		if self.wet_weight and self.dry_weight > self.wet_weight:
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

		self.cure_collect = self.cure_collect + 1
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
		self.cure_collect = self.cure_collect - 1 if self.cure_collect > 0 else 0
		self.flags.ignore_validate_update_after_submit = True
		self.save()

	@Document.whitelist
	def harvest(self, flower, other_material=None, waste=None, additional_collection=None):
		if self.disabled:
			frappe.throw("Plant <strong>{}</strong> is not available for harvesting.")

		if self.destroy_scheduled:
			frappe.throw("Plant <strong>{}</strong> is currently scheduled for destruction and cannot be harvested.")

		items = []
		frappe.flags.ignore_external_sync = True
		if other_material:
			item_group = frappe.get_doc("Item Group", {"external_id": 9})
			items.append(self.collect_item(item_group, other_material))

		if waste:
			item_group = frappe.get_doc("Item Group", {"external_id": 27})
			items.append(self.collect_item(item_group, waste))

		self.wet_weight = flt(self.wet_weight) + flt(flower)
		if not additional_collection:
			self.state = "Drying"

		# Reset harvest_scheduled status
		self.harvest_scheduled = 0
		self.harvest_schedule_time = None
		self.harvest_collect = self.harvest_collect + 1
		self.flags.ignore_validate_update_after_submit = True
		self.save()

		self.run_method("after_harvest", items=items, flower=flower, other_material=other_material, waste=waste, additional_collection=additional_collection)

		return {"items": items}

	@Document.whitelist
	def harvest_undo(self):
		if self.state != "Drying":
			frappe.throw("Invalid action")

		self.run_method("before_harvest_undo")

		self.delete_related_items()

		self.wet_weight = 0
		self.dry_weight = 0
		self.harvest_collect = self.harvest_collect - 1 if self.harvest_collect > 0 else 0
		self.state = "Growing"

		self.flags.ignore_validate_update_after_submit = True
		self.save()

	@Document.whitelist
	def destroy_schedule(self, reason, reason_txt=None, override=None):
		if self.destroy_scheduled and not override:
			frappe.throw(
				"Plant <strong>{}</strong> has already been scheduled for destruction.".format(
					self.name))

		reason_type = removal_reasons.keys()[removal_reasons.values().index(reason)]

		if not self.flags.ignore_hooks:
			self.run_method("on_destroy_schedule", reason_type=reason_type, reason=reason_txt, override=override)

		self.destroy_scheduled = 1
		self.remove_reason = reason_txt or reason
		self.remove_time = now()
		self.flags.ignore_validate_update_after_submit = True
		self.save()

	@Document.whitelist
	def destroy_schedule_undo(self):
		if not self.destroy_scheduled:
			return

		self.run_method("on_destroy_schedule", undo=True)
		self.flags.ignore_validate_update_after_submit = True
		self.destroy_scheduled = 0
		self.remove_reason = None
		self.remove_time = None
		self.save()

	@Document.whitelist
	def harvest_schedule(self):
		if self.harvest_scheduled:
			frappe.throw("Plant <strong>{}</strong> has been scheduled for harvest.".format(self.name))

		if not self.flags.ignore_hooks:
			self.run_method("on_harvest_schedule")

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

		self.run_method("on_harvest_schedule", undo=True)

		self.harvest_scheduled = 0
		self.harvest_schedule_time = None

		self.flags.ignore_validate_update_after_submit = True
		self.save()

	@Document.whitelist
	def convert_to_inventory(self):
		item_group = frappe.get_doc("Item Group", {"external_id": 12})  # Mature Plant
		qty = 1
		item = self.collect_item(item_group, qty)

		# destroy plant as well
		self.destroy_scheduled = 1
		self.remove_time = now()
		self.disabled = 1

		self.flags.ignore_validate_update_after_submit = True
		self.save()

		self.run_method('after_convert_to_inventory', item=item)


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


@frappe.whitelist()
def move():
	"""Plant moving api"""
	items = json.loads(frappe.form_dict.get('items'))
	target = frappe.form_dict.get('target')
	plant_room = frappe.get_doc("Plant Room", target)

	plants = []
	for name in items:
		plant = frappe.get_doc("Plant", name)
		plant.move_to(plant_room)
		plants.append(plant)

	call_hook_method("plant_events", None, "on_plant_move", plants=plants, plant_room=plant_room)\

@frappe.whitelist()
def harvest_schedule():
	items = json.loads(frappe.form_dict.get('items'))

	plants = []
	for name in items:
		plant = frappe.get_doc("Plant", name)
		if not plant.harvest_scheduled:
			plant.flags.ignore_hooks = True
			plant.harvest_schedule()
			plants.append(plant)

	call_hook_method("plant_events", None, "on_harvest_schedule", plants=plants)

@frappe.whitelist()
def destroy_schedule():
	items = json.loads(frappe.form_dict.get('items'))
	reason = frappe.form_dict.get('reason')
	reason_txt = frappe.form_dict.get('reason_txt')
	override = frappe.form_dict.get('override')
	reason_type = removal_reasons.keys()[removal_reasons.values().index(reason)]

	plants = []
	for name in items:
		plant = frappe.get_doc("Plant", name)
		plant.flags.ignore_hooks = True
		plant.destroy_schedule(reason=reason, reason_txt=reason_txt, override=override)
		plants.append(plant)

	call_hook_method("plant_events", None, "on_destroy_schedule", plants=plants, reason_type=reason_type, reason=reason_txt, override=override)

@frappe.whitelist()
def get_source_details():
	source_plant = frappe.form_dict.get("source_plant")
	source_item = frappe.form_dict.get("item_code")

	if source_plant:
		source = frappe.get_doc("Plant", source_plant)
	else:
		source = frappe.get_doc("Item", source_item)

	ret = {
		"strain": source.strain,
		"item_group": source.item_group if source_item else "Mature Plant",
	}

	return ret

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
								[["disabled", "=", 0], ["destroy_scheduled", "=", 1], ["remove_time", "<", date]]):
		plant = frappe.get_doc("Plant", name)
		plant.disabled = 1
		plant.remove_time = now()
		plant.flags.ignore_validate_update_after_submit = True
		plant.save()
