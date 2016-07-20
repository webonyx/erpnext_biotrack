# -*- coding: utf-8 -*-
# Copyright (c) 2015, Webonyx and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Strain(Document):
	pass


def register_new_strain(name):
	if not name:
		return None

	name = str(name).strip()
	if not frappe.db.exists("Strain", name):
		strain = frappe.get_doc({"doctype": "Strain", "strain_name": name})
		strain.insert()

	return name
