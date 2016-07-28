from __future__ import unicode_literals
import frappe
from erpnext_biotrack.utils import disable_biotrack_sync_on_exception, make_log
from erpnext_biotrack.exceptions import BiotrackError
import vendors
import employees
import plant_rooms
import inventory_rooms
import inventories

@frappe.whitelist()
def sync():
	biotrack_settings = frappe.get_doc("BioTrack Settings")
	if biotrack_settings.enable_biotrack:
		try:

			validate_biotrack_settings(biotrack_settings)
			count_dict = {}

			count_dict["employees"] = employees.sync()
			count_dict["plant_rooms"] = plant_rooms.sync()
			count_dict["inventory_rooms"] = inventory_rooms.sync()
			count_dict["vendors"] = vendors.sync()
			count_dict["inventories"] = inventories.sync()
			# todo

			frappe.db.set_value("BioTrack Settings", None, "last_sync_datetime", frappe.utils.now())

			message = "Updated {employees} employee(s), " \
					  "{vendors} vendors, " \
					  "{plant_rooms} plant rooms(s), " \
					  "{inventory_rooms} inventory rooms(s), " \
					  "{inventories} inventories" \
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