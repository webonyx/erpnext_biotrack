from __future__ import unicode_literals

from erpnext_biotrack.biotrackthc.client import BioTrackClientError
from erpnext_biotrack.utils import make_log
from .client import post
import frappe


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


def sync(resources=None, force_sync=False, verbose=False):
	if isinstance(resources, basestring):
		resources = [resources]

	if not resources:
		resources = [
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

	make_log(title="BioTrackTHC: Sync started...", status="Queued", method="sync", message="Started")
	for name in resources:
		action = "sync_{}".format(name)
		method = frappe.get_attr("erpnext_biotrack.biotrackthc.{}.sync".format(name))
		if verbose:
			print 'Sync "{}"'.format(name)
		try:
			result = method()
			if not isinstance(result, tuple):
				result = (result, 0)

			success, fail = result
			make_log(method=action, message="synced {}, failed: {}".format(success, fail or 0))

		except BioTrackClientError as e:
			make_log(
				title="{} has terminated".format(name),
				status="Error",
				method=name,
				message=frappe.get_traceback(),
				exception=True
			)

	frappe.db.set_value("BioTrack Settings", None, "last_sync_datetime", frappe.utils.now())
	make_log(title="BioTrackTHC: Sync Completed", status="Success", method="sync", message="Completed")

	frappe.flags.force_sync = False
	frappe.flags.in_import = False
