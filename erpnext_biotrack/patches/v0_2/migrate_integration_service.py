from __future__ import unicode_literals
import frappe

def execute():
	service_name="BioTrack"
	if frappe.db.exists("Integration Service", service_name):
		integration_service = frappe.get_doc("Integration Service", service_name)
	else:
		integration_service = frappe.new_doc("Integration Service")
		integration_service.service = service_name

	integration_service.enabled = 1
	integration_service.flags.ignore_mandatory = True
	integration_service.save(ignore_permissions=True)

	settings = frappe.get_doc("BioTrack Settings")
	if not settings.synchronization:
		settings.synchronization = "All"

	if not settings.sync_frequency:
		settings.sync_frequency = "Daily"

	settings.flags.ignore_mandatory = True
	settings.save()