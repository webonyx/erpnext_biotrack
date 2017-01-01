# -*- coding: utf-8 -*-
# Copyright (c) 2015, Webonyx and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class TraceabilitySettings(Document):
	pass

@frappe.whitelist()
def get_default_warehouse():
	cultivation_warehouse = frappe.db.get_single_value("Traceability Settings",
											   "default_source_warehouse")
	harvest_warehouse = frappe.db.get_single_value("Traceability Settings",
											  "default_harvest_warehouse")

	return {"cultivation_warehouse": cultivation_warehouse, "harvest_warehouse": harvest_warehouse}