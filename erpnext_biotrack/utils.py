# -*- coding: utf-8 -*-
# Copyright (c) 2016, Webonyx and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from .exceptions import BiotrackSetupError

def disable_biotrack_sync_on_exception():
	frappe.db.rollback()
	frappe.db.set_value("Biotrack Settings", None, "enable_biotrack", 0)
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
name=None, request_data={}): pass