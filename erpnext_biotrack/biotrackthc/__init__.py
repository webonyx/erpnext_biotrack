from __future__ import unicode_literals

from erpnext_biotrack.biotrackthc.client import BioTrackClientError
from .client import post
import frappe
from frappe.integration_broker.doctype.integration_service.integration_service import get_integration_controller

def sync_up_enabled():
	if frappe.flags.in_import or frappe.flags.in_test:
		return False

	settings = frappe.get_doc("BioTrack Settings")
	return settings.is_sync_up_enabled()

def get_location():
	return frappe.get_value("BioTrack Settings", None, "location")


def call(fn, *args, **kwargs):
	if frappe.conf.get("biotrack.developer_mode"):
		from .client_dev import post as post_dev
		return post_dev(fn, *args, **kwargs)

	return post(fn, *args, **kwargs)


def map_resources(doctype):
	resources = []

	if doctype == "Plant":
		resources.append("plant")
	elif doctype == "Plant Room":
		resources.append("plant_room")
	elif doctype == "Item":
		resources.append("inventory")
		resources.append("plant")
	elif doctype == "Customer":
		resources.append("vendor")
	elif doctype == "Employee":
		resources.append("employee")
	elif doctype == "Quality Inspection":
		resources.append("qa_sample")
	elif doctype == "Warehouse":
		resources.append("inventory_room")

	return resources

def sync(doctype=None, resources=None, force_sync=False, async_notify=False):
	main_resources = []

	if not resources:
		resources = []

	elif isinstance(resources, basestring):
		resources = [resources]

	if doctype:
		main_resources = map_resources(doctype)
		main_resources += resources

	if not main_resources:
		main_resources = [
			"employee",
			"plant_room",
			"inventory_room",
			"vendor",
			"inventory",
			"plant",
			"manifest",
			"qa_lab",
			"qa_sample",
		]

	frappe.flags.force_sync = force_sync
	frappe.flags.in_import = True

	if async_notify:
		frappe.publish_realtime("msgprint", {"message": "Sync started", "alert": True})

	for name in main_resources:
		method = frappe.get_attr("erpnext_biotrack.biotrackthc.{}.sync".format(name))
		try:
			method()
		except Exception as e:
			make_log(name, frappe.get_traceback() or e.message, "Failed")

	if not doctype:
		frappe.db.set_value("BioTrack Settings", None, "last_sync_datetime", frappe.utils.now())
		make_log("Sync Completed")

	if async_notify:
		frappe.publish_realtime("msgprint", {"message": "Sync completed", "alert": True})
		if doctype:
			frappe.publish_realtime("list_update", {"doctype": doctype})

	frappe.flags.force_sync = False
	frappe.flags.in_import = False

def make_log(action, data=None, status='Completed'):
	service = get_integration_controller("BioTrack")
	integration_req = service.create_request(data)
	integration_req.action = action
	integration_req.status = status
	integration_req.save()