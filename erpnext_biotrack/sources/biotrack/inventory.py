from __future__ import unicode_literals
import frappe, os
from erpnext_biotrack.biotrackthc.inventory import sync as sync_inventory

@frappe.whitelist()
def sync():
	return sync_inventory()
