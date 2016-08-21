# -*- coding: utf-8 -*-
# Copyright (c) 2016, Webonyx and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

def find_strain(name):
	name = str(name).strip()

	if name and not frappe.db.exists("Strain", name):
		strain = frappe.get_doc({"doctype": "Strain", "strain_name": name})
		strain.insert()

	return name