# -*- coding: utf-8 -*-
# Copyright (c) 2015, Webonyx and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from erpnext_biotrack.biotrackthc.inventory_room import get_default_warehouse
from frappe import _
from frappe.model.document import Document
from erpnext_biotrack.item_utils import make_item, generate_item_code

class PlantEntry(Document):
	def before_submit(self):
		def validate_plant(doc, plant):
			if plant.docstatus != 1 or plant.disabled:
				frappe.throw(_("Plant {0} is not active.").format(plant.name))

			if plant.destroy_scheduled:
				frappe.throw(_("Plant {0} has been scheduled for destruction.").format(plant.name))

		def validate_harvest(doc, plant):
			if not plant.harvest_scheduled:
				frappe.throw(_("Plant {0} has not been scheduled for harvest.").format(plant.name))

			if plant.state != "Growing":
				frappe.throw(_("Plant {0} must be in <strong>Growing</strong> state for harvest.").format(plant.name))

		def validate_cure(doc, plant):
			if plant.state != "Drying":
				frappe.throw(_("Plant {0} must be in <strong>Drying</strong> state for convert.").format(plant.name))

		self.process_plants(validate_plant)

		if self.purpose == "Harvest":
			self.process_plants(validate_harvest)
		elif self.purpose == "Convert":
			self.process_plants(validate_cure)

		self.make_derivatives()

	def on_submit(self):
		def after_harvest(doc, plant):
			if not doc.additional_collections:
				plant.state = "Drying"

			plant.harvest_scheduled = 0
			plant.harvest_schedule_time = None
			plant.harvest_collect = plant.harvest_collect + 1
			plant.flags.ignore_validate_update_after_submit = True
			plant.save()

		def after_convert(doc, plant):
			if not doc.additional_collections:
				plant.disabled = 1

			plant.cure_collect = plant.cure_collect + 1
			plant.flags.ignore_validate_update_after_submit = True
			plant.save()

		if self.purpose == "Harvest":
			self.process_plants(after_harvest)
		elif self.purpose == "Convert":
			self.process_plants(after_convert)

	def get_strain(self):
		if self.strain:
			return self.strain

		plant = self.plants[0]
		return frappe.get_value("Plant", plant.plant_code, "strain")

	def make_derivatives(self):
		self.items = []
		frappe.flags.ignore_external_sync = True

		if self.purpose == "Convert":
			self.items.append(self.collect_item({"external_id": 6}, self.flower))

		if self.other_material:
			self.items.append(self.collect_item({"external_id": 9}, self.other_material))

		if self.waste:
			self.items.append(self.collect_item({"external_id": 27}, self.waste))

	def process_plants(self, update):
		for ple_detail in self.get("plants"):
			plant = frappe.get_doc("Plant", ple_detail.plant_code)
			update(self, plant)

	def collect_item(self, item_group_filter, qty):
		item_group = frappe.get_doc("Item Group", item_group_filter)
		strain = self.get_strain()
		default_warehouse = get_default_warehouse()

		return make_item(properties={
			"item_name": " ".join([strain, item_group.item_group_name]),
			"item_code": generate_item_code(),
			"item_group": item_group.name,
			"default_warehouse": default_warehouse.name,
			"strain": strain,
			"stock_uom": "Gram",
			"is_stock_item": 1,
			"plant_entry": self.name,
		}, qty=qty)

	def get_plants(self):
		self.set('plants', [])
		filters = {
			"disabled" : 0
		}

		if self.strain:
			filters["strain"] = self.strain

		if self.purpose == "Harvest":
			filters["harvest_scheduled"] = 1

		elif self.purpose == "Convert":
			filters["state"] = "Drying"

		if self.from_plant_room:
			filters["plant_room"] = self.from_plant_room

		for plant in frappe.get_all("Plant", fields=["name", "strain"], filters=filters):
			ple_child = self.append('plants')
			ple_child.plant_code = plant.name
			ple_child.strain = plant.strain
			ple_child.uom = "Gram"

	def get_plant_details(self, args=None):
		plant = frappe.db.sql("""select title, strain from `tabPlant`
					where name = %s and disabled=0""", (args.get('plant_code')), as_dict=1)
		if not plant:
			frappe.throw(_("Plant {0} is not active").format(args.get("plant_code")))

		plant = plant[0]

		ret = {
			"strain": plant.strain
		}

		return ret