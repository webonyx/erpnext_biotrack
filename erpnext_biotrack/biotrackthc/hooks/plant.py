import sys
import frappe
from erpnext_biotrack.biotrackthc import sync_up_enabled, get_location, call
from frappe.utils.data import cstr, cint, flt


def call_hook(plant, method, *args, **kwargs):
	if not sync_up_enabled():
		return

	if plant:
		# doc events
		return getattr(sys.modules[__name__], method)(plant, *args, **kwargs)
	else:
		# events with multiple plants
		return getattr(sys.modules[__name__], method)(*args, **kwargs)


def is_bio_plant(plant):
	return cstr(plant.get("bio_barcode")) != ""


def on_submit(plant):
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


def on_cancel(plant):
	"""Call plant_new_undo api"""
	if not is_bio_plant(plant):
		return

	# Barcode 9160883599199700 is no longer in a state where it can be un-done.
	call("plant_new_undo", {
		"barcodeid": [plant.bio_barcode],
	})

def on_trash(plant):
	if not is_bio_plant(plant):
		return

	try:
		call("plant_destroy", {
			"barcodeid": [plant.bio_barcode],
		})
	except Exception as e:
		frappe.local.message_log.pop()

def on_plant_move(plants, plant_room):
	if not plant_room.external_id:
		return

	barcodeid = []
	for plant in plants:
		if is_bio_plant(plant):
			barcodeid.append(plant.get("bio_barcode"))

	if len(barcodeid):
		try:
			call("plant_move", {
				"room": plant_room.external_id,
				"barcodeid": barcodeid,
			})
		except Exception as e:
			frappe.local.message_log.pop()


def on_harvest_schedule(plants, undo=False):
	barcodeid = []
	if not isinstance(plants, list):
		plants = [plants]

	for plant in plants:
		if is_bio_plant(plant):
			barcodeid.append(plant.get("bio_barcode"))

	if len(barcodeid):
		# figure out err: # Barcode 9160883599199700 is no longer in a state where it can be harvested
		if undo:
			try:
				call("plant_harvest_schedule_undo", {
					"barcodeid": barcodeid,
				})
			except Exception as e:
				# ignore error
				frappe.local.message_log.pop()
		else:
			call("plant_harvest_schedule", {
				"barcodeid": barcodeid,
			})

def on_destroy_schedule(plants, reason_type=None, reason=None, override=None, undo=False):
	barcodeid = []
	if not isinstance(plants, list):
		plants = [plants]

	for plant in plants:
		if is_bio_plant(plant):
			barcodeid.append(plant.get("bio_barcode"))

	if len(barcodeid):
		if not undo and not reason_type:
			frappe.throw("Reason type is required")

		if undo:
			try:
				call("plant_destroy_schedule_undo", {
					"barcodeid": barcodeid,
				})
			except Exception as e:
				frappe.local.message_log.pop()
				# ignore error
				pass
		else:
			call("plant_destroy_schedule", {
				"barcodeid": barcodeid,
				"reason_extended": reason_type,
				"reason": reason,
				"override": override or 0
			})


def after_harvest(plant, items, flower, other_material=None, waste=None, additional_collection=None):
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

def before_harvest_undo(plant):
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


def after_cure(plant, items, flower, other_material=None, waste=None, additional_collection=None):
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

def after_convert_to_inventory(plant, item):
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