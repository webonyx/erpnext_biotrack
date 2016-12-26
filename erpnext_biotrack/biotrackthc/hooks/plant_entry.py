import sys
import frappe
from erpnext_biotrack.biotrackthc import sync_up_enabled, get_location, call
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

	action = "plant_harvest" if plant_entry.purpose == "Harvest" else "plant_cure"
	res = None

	try:
		res = call(action, {
			"barcodeid": barcodeid,
			"location": get_location(),
			"weights": make_weights_data(plant_entry.flower, plant_entry.other_material, plant_entry.waste),
			"collectadditional": cint(plant_entry.additional_collections),
		})
	except Exception as e:
		frappe.throw(frappe.local.message_log.pop(), title="BioTrackTHC sync up failed")

	if res:
		items = plant_entry.items or []
		map_item_derivatives(items, res.get("derivatives", []))

