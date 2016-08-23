# -*- coding: utf-8 -*-
# Copyright (c) 2016, Webonyx and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import json, os
import frappe
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

from .biotrackthc import call as biotrackthc_call

@frappe.whitelist()
def new_item(item_name, item_group, strain, actual_qty, default_warehouse):
	item_group = frappe.get_doc("Item Group", item_group)
	location = frappe.get_value("BioTrack Settings", None, "location")

	data = biotrackthc_call("inventory_new", data={
		"data": {
			"invtype": item_group.external_id,
			"quantity": actual_qty,
			"strain": strain,
		},
		"location": location
	})

	barcode = data['barcode_id'][0]
	item = frappe.new_doc("Item")
	item.update({
		"item_name": item_name,
		"item_code": barcode,
		"barcode": barcode,
		"item_group": item_group.name,
		"default_warehouse": default_warehouse,
		"strain": strain,
		"stock_uom": "Gram",
		"is_stock_item": 1,
	})

	item.insert()
	make_stock_entry(item_code=barcode, target=default_warehouse, qty=actual_qty)

	return item

@frappe.whitelist()
def clone_item(item_code, qty, rate):
	# @todo call inventory_split
	parent = frappe.get_doc("Item", item_code)
	item = frappe.get_doc({
		"doctype": "Item",
		"item_code": "Sub Lot/Batch Test",
		"item_name": "Sub Lot/Batch Test",
		"item_group": parent.item_group,
	})

	biotrackthc_call("")

	return item