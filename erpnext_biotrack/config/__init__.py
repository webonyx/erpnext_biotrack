from __future__ import unicode_literals
import frappe

def is_training_mode():
	return int(frappe.get_value("Biotrack Settings", None, 'is_training')) or 0
