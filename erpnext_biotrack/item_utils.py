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
		"actual_qty": actual_qty,
	})

	item.insert()
	make_stock_entry(item_code=barcode, target=default_warehouse, qty=actual_qty)

	return item

@frappe.whitelist()
def clone_item(item_code, qty, rate, default_warehouse):
	data = biotrackthc_call("inventory_split", data={
		"data": [
			{
				"barcodeid": item_code,
				"remove_quantity": qty
			}
		]
	})

	parent = frappe.get_doc("Item", item_code)
	barcode = data['barcode_id'][0]

	item = frappe.get_doc({
		"doctype": "Item",
		"item_name": barcode,
		"item_code": barcode,
		"barcode": barcode,
		"item_parent": parent.name,
		"item_group": parent.item_group,
		"default_warehouse": default_warehouse,
		"strain": parent.strain,
		"stock_uom": parent.stock_uom,
		"is_stock_item": 1,
		"actual_qty": qty,
	})

	item.insert()
	make_stock_entry(item_code=barcode, target=default_warehouse, qty=qty)

	parent.append("sub_items", {
		"item_code": item.item_code,
		"qty": qty
	})
	remaining_qty = float(parent.actual_qty) - float(qty)

	stock_reco = frappe.new_doc("Stock Reconciliation")
	stock_reco.posting_date = frappe.flags.current_date
	stock_reco.append("items", {
		"item_code": parent.item_code,
		"warehouse": default_warehouse,
		"qty": remaining_qty,
		"valuation_rate": rate or 1,
	})
	stock_reco.save()
	stock_reco.submit()

	parent.actual_qty = remaining_qty
	parent.save()

	return item.as_dict()