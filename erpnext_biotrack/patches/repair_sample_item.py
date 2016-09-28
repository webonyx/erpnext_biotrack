from __future__ import unicode_literals
import frappe
from erpnext_biotrack.biotrackthc.inventory import get_biotrack_inventories
from frappe.utils.data import cint, cstr


def execute():
	for biotrack_inventory in get_biotrack_inventories():
		barcode = cstr(biotrack_inventory.get("id"))
		is_sample = cint(biotrack_inventory.get("is_sample"))

		if is_sample:
			frappe.db.set_value("Item", barcode, "is_sample", 1)
