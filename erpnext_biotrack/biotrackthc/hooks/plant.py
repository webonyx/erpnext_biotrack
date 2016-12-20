import sys
import frappe
from erpnext_biotrack.biotrackthc import sync_up_enabled, get_location, call
from frappe.utils.data import cstr, cint, flt


def call_hook(plant, method, *args, **kwargs):
	if not sync_up_enabled():
		return

	return getattr(sys.modules[__name__], method)(plant, method, *args, **kwargs)


def is_bio_plant(plant):
	return cstr(plant.get("bio_barcode")) != ""


def on_submit(plant, method):
	# only root plant get handled
	if plant.flags.in_bulk:
		return

	plants = plant.flags.bulk_plants or []
	plants.append(plant)

	if len(plants) != plant.get("qty"):
		frappe.throw("Bulk adding qty mismatch")

	plant_room = frappe.get_doc("Plant Room", plant.get("plant_room"))
	result = call("plant_new", {
		"room": plant_room.external_id,
		"quantity": plant.get("qty"),
		"strain": plant.get("strain"),
		"source": plant.get("item_code"),
		"mother": cint(plant.get("is_mother")),
		"location": get_location()
	})

	for idx, barcode in enumerate(result.get("barcode_id")):
		doc = plants[idx]
		doc.set("bio_barcode", barcode)
		doc.flags.ignore_validate_update_after_submit = True
		doc.save()


def on_cancel(plant, method):
	"""Call plant_new_undo api"""
	if not is_bio_plant(plant):
		return

	# Barcode 9160883599199700 is no longer in a state where it can be un-done.
	call("plant_new_undo", {
		"barcodeid": [plant.bio_barcode],
	})

def on_trash(plant, method):
	if not is_bio_plant(plant):
		return

	try:
		call("plant_destroy", {
			"barcodeid": [plant.bio_barcode],
		})
	except Exception as e:
		frappe.local.message_log.pop()

def before_harvest_schedule(plant, method):
	if not is_bio_plant(plant):
		return

	# Barcode 9160883599199700 is no longer in a state where it can be harvested
	call("plant_harvest_schedule", {
		"barcodeid": [plant.bio_barcode],
	})

def before_harvest_schedule_undo(plant, method):
	if not is_bio_plant(plant):
		return

	try:
		call("plant_harvest_schedule_undo", {
			"barcodeid": [plant.bio_barcode],
		})
	except Exception as e:
		frappe.local.message_log.pop()
		# ignore error
		pass

def before_destroy_schedule(plant, method, *args, **kwargs):
	if not is_bio_plant(plant):
		return

	if not "reason_key" in kwargs:
		frappe.throw('"reason_key" is missing')

	call("plant_destroy_schedule", {
		"barcodeid": [plant.bio_barcode],
		"reason_extended": kwargs.get("reason_key"),
		"reason": kwargs.get("reason"),
		"override": 1 if kwargs.get("override") else 0
	})

def before_destroy_schedule_undo(plant, method):
	if not is_bio_plant(plant):
		return

	try:
		call("plant_destroy_schedule_undo", {
			"barcodeid": [plant.bio_barcode],
		})
	except Exception as e:
		frappe.local.message_log.pop()
		# ignore error
		pass

def after_harvest(plant, method, items, flower, other_material=None, waste=None, additional_collection=None):
	if not is_bio_plant(plant):
		return

	res = call("plant_harvest", {
		"barcodeid": plant.bio_barcode,
		"location": get_location(),
		"weights": make_weights_data(flower, other_material, waste),
		"collectadditional": cint(additional_collection),
	})

	map_item_derivatives(items, res.get("derivatives", []))
	frappe.db.set_value("Plant", plant.name, "bio_transaction_id", res.get("transactionid"))

def before_harvest_undo(plant, method):
	if not is_bio_plant(plant):
		return

	if not plant.get("bio_transaction_id"):
		return

	try:
		call("plant_harvest_undo", {
			"transactionid": plant.get("bio_transaction_id"),
		})
	except Exception as e:
		frappe.local.message_log.pop()
		# ignore error
		pass

	frappe.db.set_value("Plant", plant.name, "bio_transaction_id", None)


def after_cure(plant, method, items, flower, other_material=None, waste=None, additional_collection=None):
	if not is_bio_plant(plant):
		return

	res = call("plant_cure", {
		"barcodeid": plant.bio_barcode,
		"location": get_location(),
		"weights": make_weights_data(flower, other_material, waste),
		"collectadditional": cint(additional_collection),
	})

	map_item_derivatives(items, res.get("derivatives", []))
	frappe.db.set_value("Plant", plant.name, "bio_transaction_id", res.get("transactionid"))

def after_convert_to_inventory(plant, method, item):
	if not is_bio_plant(plant):
		return

	res = call("plant_convert_to_inventory", {
		"barcodeid": plant.bio_barcode
	})

	frappe.db.set_value("Item", item.name, "bio_barcode", plant.bio_barcode)
	frappe.db.set_value("Plant", plant.name, "bio_transaction_id", res.get("transactionid"))

def make_weights_data(flower, other_material=None, waste=None):
	amount_map = {
		6: flt(flower),
		9: flt(other_material),
		27: flt(waste),
	}

	weights = [
		{
			"amount": amount_map[6],
			"invtype": 6,
			"uom": "g"
		}
	]

	if other_material:
		weights.append({
			"amount": amount_map[9],
			"invtype": 9,
			"uom": "g"
		})

	if waste:
		weights.append({
			"amount": amount_map[27],
			"invtype": 27,
			"uom": "g"
		})

	return weights

def map_item_derivatives(items, derivatives):
	for derivative in derivatives:
		item_group = frappe.get_doc("Item Group", {"external_id": derivative.get("barcode_type")})
		for item in items:
			if item.item_group == item_group.name:
				item.set("barcode", derivative.get("barcode_id"))
				item.save()