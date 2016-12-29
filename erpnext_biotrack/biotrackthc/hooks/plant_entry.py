import sys
import frappe
from erpnext_biotrack.biotrackthc import sync_up_enabled, get_location, call
from erpnext_biotrack.biotrackthc.client import BioTrackClientError
from erpnext_biotrack.biotrackthc.hooks.plant import is_bio_plant, make_weights_data, map_item_derivatives
from frappe.utils.data import cstr, cint, flt


def call_hook(plant_entry, method, *args, **kwargs):
	if not sync_up_enabled():
		return

	return getattr(sys.modules[__name__], method)(plant_entry, *args, **kwargs)

def before_submit(plant_entry):
	"""BioTrack sync up: inventory_new or inventory_adjust"""
	barcodeid = []
	for ple_detail in plant_entry.get("plants"):
		plant = frappe.get_doc("Plant", ple_detail.plant_code)
		if is_bio_plant(plant):
			barcodeid.append(plant.get("bio_barcode"))

	if len(barcodeid) == 0:
		return

	if plant_entry.purpose == "Convert":
		convert_on_submit(plant_entry, barcodeid)
		return

	action = "plant_harvest" if plant_entry.purpose == "Harvest" else "plant_cure"
	res = None

	try:
		res = call(action, {
			"barcodeid": barcodeid,
			"location": get_location(),
			"weights": make_weights_data(plant_entry.flower, plant_entry.other_material, plant_entry.waste),
			"collectadditional": cint(plant_entry.additional_collections),
		})
	except BioTrackClientError as e:
		frappe.throw(cstr(e.message), title="BioTrackTHC sync up failed")

	if res:
		plant_entry.bio_transaction = res.get("transactionid")
		items = plant_entry.items or {}
		map_item_derivatives(items, res.get("derivatives", []))


def convert_on_submit(plant_entry, barcodeid):
	res = None
	try:
		res = call("plant_convert_to_inventory", {
			"barcodeid": barcodeid
		})
	except BioTrackClientError as e:
		frappe.throw(cstr(e.message), title="BioTrackTHC sync up failed")

	if res:
		plant_entry.bio_transaction = res.get("transactionid")
		items = plant_entry.items or {}
		for name in items:
			item = items[name]
			if not item.barcode:
				plant = frappe.get_doc("Plant", name)
				if is_bio_plant(plant):
					item.barcode = plant.get("bio_barcode")
					item.bio_barcode = plant.get("bio_barcode")
					item.save()

def before_cancel(plant_entry):
	if plant_entry.purpose == "Convert" or not plant_entry.bio_transaction:
		return

	if plant_entry.purpose == "Harvest":
		action =  "plant_harvest_undo"
	else:
		action = "plant_cure_undo"

	try:
		call(action, {
			"transactionid": plant_entry.bio_transaction
		})
	except BioTrackClientError as e:
		frappe.throw(cstr(e.message), title="BioTrackTHC sync up failed")

	plant_entry.bio_transaction = ""