from __future__ import unicode_literals
import frappe
from erpnext_biotrack.utils import disable_biotrack_sync_on_exception, make_log
from erpnext_biotrack.exceptions import BiotrackError
import vendor
import employee
import plant_room
import inventory_room
import plant
import inventory
import manifest
import qa_lab
import qa_sample

@frappe.whitelist()
def sync():
	biotrack_settings = frappe.get_doc("BioTrack Settings")
	if biotrack_settings.enable_biotrack:
		try:

			validate_biotrack_settings(biotrack_settings)
			count_dict = {}

			count_dict["employees"] = employee.sync()
			count_dict["plant_rooms"] = plant_room.sync()
			count_dict["inventory_rooms"] = inventory_room.sync()
			count_dict["vendors"] = vendor.sync()
			count_dict["plants"] = plant.sync()
			count_dict["inventories"] = inventory.sync()
			count_dict["manifests"] = manifest.sync()
			count_dict["qa_labs"] = qa_lab.sync()
			count_dict["qa_samples"] = qa_sample.sync()

			frappe.db.set_value("BioTrack Settings", None, "last_sync_datetime", frappe.utils.now())

			message = "Updated {employees} employee(s), " \
					  "{vendors} vendors, " \
					  "{plant_rooms} plant rooms, " \
					  "{inventory_rooms} inventory rooms, " \
					  "{plants} plant(s), " \
					  "{inventories} inventories" \
					  "{manifests} manifests" \
				.format(**count_dict)

			make_log(method="biotrack.sync", message=message)

		except Exception as e:
			message = frappe.get_traceback()
			make_log(
				title="sync has terminated",
				status="Error",
				method="biotrack.sync",
				message=message,
				exception=True
			)
	else:
		make_log(
			method="biotrack.sync",
			status="Error",
			message="BioTrack source is not enabled"
		)

	return len([])

def validate_biotrack_settings(biotrack_settings):
	"""
		This will validate mandatory fields and app credentials
		by calling validate() of biotrack settings.
	"""
	try:
		biotrack_settings.save()
	except BiotrackError:
		disable_biotrack_sync_on_exception()