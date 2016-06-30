# -*- coding: utf-8 -*-
# Copyright Webonyx and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from .exceptions import BiotrackError
from .utils import disable_biotrack_sync_on_exception, make_biotrack_log
from .sync_employees import sync_employees

@frappe.whitelist()
def sync_biotrack():
	"Enqueue longjob for syncing biotrack."

	try:
		from frappe.utils.background_jobs import enqueue
		enqueue(sync_biotrack_resources)
	except:
		# Try this shit since rq is still in development branch
		from frappe.tasks import scheduler_task
		scheduler_task.delay(site=frappe.local.site, event="hourly_long",
							 handler="erpnext_biotrack.tasks.sync_biotrack_resources")

	frappe.msgprint(_("Queued for syncing. It may take a few minutes to an hour if this is your first sync."))

def sync_biotrack_resources():
	biotrack_settings = frappe.get_doc("Biotrack Settings")

	make_biotrack_log(title="Sync Job Queued", status="Queued", method=frappe.local.form_dict.cmd, message="Sync Job Queued")
	
	if biotrack_settings.enable_biotrack:
		try :
			now_time = frappe.utils.now()
			validate_biotrack_settings(biotrack_settings)
			frappe.local.form_dict.count_dict = {}

			frappe.local.form_dict.count_dict["employees"] = sync_employees()
			# todo

			frappe.db.set_value("Biotrack Settings", None, "last_sync_datetime", now_time)
			
			make_biotrack_log(title="Sync Completed", status="Success", method=frappe.local.form_dict.cmd,
				message= "Updated {employees} employee(s)".format(**frappe.local.form_dict.count_dict))

		except Exception as e:
			make_biotrack_log(title="sync has terminated", status="Error", method="sync_biotrack_resources",
				message=frappe.get_traceback(), exception=True)
					
	elif frappe.local.form_dict.cmd == "erpnext_biotrack.api.sync_biotrack":
		make_biotrack_log(
			title="Biotrack connector is disabled",
			status="Error",
			method="sync_biotrack_resources",
			message=_("""Biotrack connector is not enabled"""),
			exception=True)

def validate_biotrack_settings(biotrack_settings):
	"""
		This will validate mandatory fields and app credentials
		by calling validate() of biotrack settings.
	"""
	try:
		biotrack_settings.save()
	except BiotrackError:
		disable_biotrack_sync_on_exception()
