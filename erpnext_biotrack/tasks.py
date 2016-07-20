# -*- coding: utf-8 -*-
# Copyright Webonyx and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from .exceptions import BiotrackError
from .utils import disable_biotrack_sync_on_exception, make_biotrack_log
from .sync_employees import sync_employees
from .sync_customers import sync as sync_customers
import sync_plant_room
import sync_inventory_room
import sync_inventory


@frappe.whitelist()
def sync_biotrack():
	"Enqueue longjob for syncing biotrack."

	try:
		from frappe.utils.background_jobs import enqueue
		enqueue(sync_biotrack_resources)
	except:
		# Try this shit since rq is still in development branch
		from frappe.tasks import scheduler_task
		scheduler_task.delay(site=frappe.local.site, event="all",
							 handler="erpnext_biotrack.tasks.sync_biotrack_resources")

	frappe.msgprint(_("Queued for syncing. It may take a few minutes to an hour if this is your first sync."))


def sync_biotrack_resources():
	biotrack_settings = frappe.get_doc("BioTrack Settings")
	make_biotrack_log(title="Sync Job Queued", status="Queued", method=frappe.local.form_dict.cmd,
					  message="Sync Job Queued")

	if biotrack_settings.enable_biotrack:
		try:
			now_time = frappe.utils.now()
			validate_biotrack_settings(biotrack_settings)
			count_dict = {}
			count_dict["employees"] = sync_employees()
			count_dict["plant_rooms"] = sync_plant_room.sync()
			count_dict["inventory_rooms"] = sync_inventory_room.sync()
			count_dict["customers"] = sync_customers()
			count_dict["inventories"] = sync_inventory.sync()
			# todo

			frappe.db.set_value("BioTrack Settings", None, "last_sync_datetime", now_time)

			message="Updated {employees} employee(s), " \
					  "{customers} customer(s), " \
					  "{plant_rooms} plant rooms(s), " \
					  "{inventory_rooms} inventory rooms(s), " \
					  "{inventories} inventories" \
				.format(**count_dict)

			make_biotrack_log(title="Sync Completed", status="Success", method=frappe.local.form_dict.cmd, message=message)

		except Exception as e:
			message=frappe.get_traceback()
			make_biotrack_log(
				title="sync has terminated",
				status="Error",
				method="sync_biotrack_resources",
				message=message,
				exception=True
			)

	else:
		message=_("""BioTrack connector is not enabled""")
		make_biotrack_log(
			title="BioTrack connector is disabled",
			status="Error",
			method="sync_biotrack_resources",
			message=message,
			exception=True)

	return message


def validate_biotrack_settings(biotrack_settings):
	"""
		This will validate mandatory fields and app credentials
		by calling validate() of biotrack settings.
	"""
	try:
		biotrack_settings.save()
	except BiotrackError:
		disable_biotrack_sync_on_exception()


def hourly():
	return sync_if('Hourly')


def daily():
	return sync_if('Daily')


def weekly():
	return sync_if('Weekly')


def sync_if(schedule, default='Daily'):
	schedule_config = frappe.get_value("BioTrack Settings", None, 'schedule_in') or default

	if schedule_config == schedule:
		sync_biotrack()
