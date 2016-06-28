# -*- coding: utf-8 -*-
# Copyright (c) 2016, Webonyx and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import json
import frappe
from .exceptions import BiotrackSetupError
from .exceptions import BiotrackError

def get_biotrack_settings():
	d = frappe.get_doc("Biotrack Settings")
	d.password = d.get_password()

	if d.username and d.license_number:
		return d.as_dict()
	else:
		frappe.throw(_("Biotrack credentials are not configured on Biotrack Settings"), BiotrackError)



def disable_biotrack_sync_on_exception():
	frappe.db.rollback()
	frappe.db.set_value("Biotrack Settings", None, "enable_biotrack", 0)
	frappe.db.set_value("Biotrack Settings", None, "session_id", '')
	frappe.db.commit()


def is_biotrack_enabled():
	biotrack_settings = frappe.get_doc("Biotrack Settings")
	if not biotrack_settings.enable_biotrack:
		return False
	try:
		biotrack_settings.validate()
	except BiotrackSetupError:
		return False
	
	return True
	
def make_biotrack_log(title="Sync Log", status="Queued", method="sync_biotrack", message=None, exception=False,
name=None, request_data={}):
	if not name:
		name = frappe.db.get_value("Biotrack Log", {"status": "Queued"})

		if name:
			""" if name not provided by log calling method then fetch existing queued state log"""
			log = frappe.get_doc("Biotrack Log", name)

		else:
			""" if queued job is not found create a new one."""
			log = frappe.get_doc({"doctype": "Biotrack Log"}).insert(ignore_permissions=True)

		if exception:
			frappe.db.rollback()
			log = frappe.get_doc({"doctype": "Biotrack Log"}).insert(ignore_permissions=True)

		log.message = message if message else frappe.get_traceback()
		log.title = title[0:140]
		log.method = method
		log.status = status
		log.request_data = json.dumps(request_data)

		log.save(ignore_permissions=True)
		frappe.db.commit()