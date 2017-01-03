import sys
import frappe
from erpnext_biotrack.biotrackthc import sync_up_enabled, get_location, call
from erpnext_biotrack.biotrackthc.client import BioTrackClientError
from frappe.utils.data import cstr, cint


def call_hook(plant_entry, method, *args, **kwargs):
	if not sync_up_enabled():
		return

	return getattr(sys.modules[__name__], method)(plant_entry, *args, **kwargs)

def is_bio_plant_room(doc):
	return cint(doc.get("bio_id")) != 0

def after_insert(doc):
	bio_id = generate_id(doc)
	try:
		res = call("plant_room_add", {
			"id": bio_id,
			"name": doc.plant_room_name,
			"location": get_location(),
		})
	except BioTrackClientError as e:
		frappe.throw(cstr(e.message), title="BioTrackTHC sync up failed")
	else:
		frappe.db.set_value(doc.doctype, doc.name, {
			"bio_id": bio_id,
			"bio_name": doc.plant_room_name,
			"bio_transactionid": res.get("transactionid")
		}, None, update_modified=False)

def on_update(doc):
	if is_bio_plant_room(doc) and doc.plant_room_name != doc.bio_name:
		frappe.log(doc.plant_room_name)
		frappe.log(doc.bio_name)
		try:
			res = call("plant_room_modify", {
				"id": doc.bio_id,
				"name": doc.plant_room_name,
				"location": get_location(),
			})
		except BioTrackClientError as e:
			frappe.throw(cstr(e.message), title="BioTrackTHC sync up failed")
		else:
			frappe.db.set_value(doc.doctype, doc.name, {
				"bio_name": doc.plant_room_name,
				"bio_transactionid": res.get("transactionid")
			}, None, update_modified=False)

def generate_id(doc, field="bio_id"):
	start_id = 1000
	last = frappe.db.sql("""select {} from `tab{}`
				order by bio_id desc limit 1""".format(field, doc.doctype))

	if last:
		last_id = last[0][0] + 1
	else:
		last_id = start_id

	return last_id

def on_trash(doc):
	if not is_bio_plant_room(doc):
		return

	try:
		call("plant_room_remove", {
			"id": doc.bio_id,
		})
	except BioTrackClientError as e:
		frappe.throw(cstr(e.message), title="BioTrackTHC sync up failed")