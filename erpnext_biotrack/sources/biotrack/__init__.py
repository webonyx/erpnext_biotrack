from __future__ import unicode_literals
import frappe
from erpnext_biotrack.utils import disable_biotrack_sync_on_exception, make_log
from erpnext_biotrack.exceptions import BiotrackError, BioTrackClientError
import vendor
import employee
import plant_room
import inventory_room
import plant
import inventory
import manifest
import qa_lab
import qa_sample

class BioTrack:
	def sync(self):
		for name in dir(self):

			if name.startswith("sync_"):
				try:
					method = getattr(self, name)
				except AttributeError:
					continue

				try:
					result = method()
					if not isinstance(result, tuple):
						result = (result, 0)

					success, fail = result

					action_name = ''.join(i for i in name if not i.isdigit())
					make_log(method=action_name, message="synced {}, failed: {}".format(success, fail or 0))

				except BioTrackClientError as e:
					make_log(
						title="{} has terminated".format(name),
						status="Error",
						method=name,
						message=frappe.get_traceback(),
						exception=True
					)

	def sync_00_employee(self):
		return employee.sync()

	def sync_01_plant_room(self):
		return plant_room.sync()

	def sync_02_inventory_room(self):
		return inventory_room.sync()

	def sync_03_vendor(self):
		return vendor.sync()

	def sync_04_inventory(self):
		return inventory.sync()

	def sync_05_plant(self):
		return plant.sync()

	def sync_06_manifest(self):
		return manifest.sync()

	def sync_07_qa_lab(self):
		return qa_lab.sync()

	def sync_08_qa_sample(self):
		return qa_sample.sync()

@frappe.whitelist()
def sync():
	biotrack_settings = frappe.get_doc("BioTrack Settings")
	# validate_biotrack_settings(biotrack_settings)
	if biotrack_settings.enable_biotrack:
		BioTrack().sync()
		frappe.db.set_value("BioTrack Settings", None, "last_sync_datetime", frappe.utils.now())
	else:
		make_log(
			method="biotrack.sync",
			status="Error",
			message="BioTrack source is not enabled"
		)


def validate_biotrack_settings(biotrack_settings):
	"""
		This will validate mandatory fields and app credentials
		by calling validate() of biotrack settings.
	"""
	try:
		biotrack_settings.save()
	except BiotrackError:
		disable_biotrack_sync_on_exception()