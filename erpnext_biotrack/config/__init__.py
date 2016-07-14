from __future__ import unicode_literals
import frappe

default_stock_warehouse_name = "Bulk Inventory room"


def is_training_mode():
	return int(frappe.get_value("BioTrack Settings", None, 'is_training')) or 0


def get_default_stock_warehouse():
	return frappe.get_doc("Warehouse", {"warehouse_name": default_stock_warehouse_name})
