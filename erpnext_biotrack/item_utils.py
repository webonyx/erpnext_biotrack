# -*- coding: utf-8 -*-
# Copyright (c) 2016, Webonyx and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from frappe.utils.data import flt

from .biotrackthc import call as biotrackthc_call


@frappe.whitelist()
def new_item(item_name, item_group, strain, actual_qty, default_warehouse, plant=None):
	item_group = frappe.get_doc("Item Group", item_group)
	location = frappe.get_value("BioTrack Settings", None, "location")

	call_data = {
		"invtype": item_group.external_id,
		"quantity": actual_qty,
		"strain": strain,
	}

	if plant:
		call_data["source_id"] = plant

	data = biotrackthc_call("inventory_new", data={
		"data": call_data,
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
		"plant": plant,
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

	# parent.append("sub_items", {
	# 	"item_code": item.item_code,
	# 	"qty": qty
	# })
	remaining_qty = flt(parent.actual_qty) - flt(qty)

	stock_reco = frappe.new_doc("Stock Reconciliation")
	stock_reco.posting_date = frappe.flags.current_date
	stock_reco.append("items", {
		"item_code": parent.item_code,
		"warehouse": default_warehouse,
		"qty": remaining_qty,
		"valuation_rate": rate or 1,
	})

	stock_reco.submit()
	parent.actual_qty = remaining_qty
	parent.save()

	return item.as_dict()

def on_validate(item, method):
	if frappe.flags.in_import or frappe.flags.in_test:
		return

	if not item.is_marijuana_item:
		return item

	missing = []
	marijuana_req_fields = ["strain", "item_group"]
	for field in marijuana_req_fields:
		if item.get(field) is None:
			missing.append(field)

	if flt(item.get("actual_qty")) == 0:
		missing.append("actual_qty")

	if not missing:
		return

	raise frappe.MandatoryError('[{doctype}, {name}]: {fields}'.format(
		fields=", ".join((each for each in missing)),
		doctype=item.doctype,
		name=item.name))

def after_insert(item, method):
	if frappe.flags.in_import or frappe.flags.in_test:
		return

	if not item.is_marijuana_item:
		return item

	item_group = frappe.get_doc("Item Group", item.item_group)
	location = frappe.get_value("BioTrack Settings", None, "location")

	call_data = {
		"invtype": item_group.external_id,
		"quantity": item.actual_qty,
		"strain": item.strain,
	}

	if item.plant:
		call_data["source_id"] = item.plant

	data = biotrackthc_call("inventory_new", data={
		"data": call_data,
		"location": location
	})

	item.update({
		"barcode": data['barcode_id'][0]
	})

	make_stock_entry(item_code=item.item_code, target=item.default_warehouse, qty=item.actual_qty)
	item.save()

def test_insert():
	item = frappe.get_doc({
		"doctype": "Item",
		"item_name": "_Test Item",
		"item_code": "_Test Item",
		"item_group": "Usable Marijuana",
		"strain": "Pineapple",
		"stock_uom": "Gram",
		"actual_qty": 50,
		"default_warehouse": "Bulk Inventory room - EV",
		"is_marijuana_item": 1,
	})

	item.save()

	# success and tear down
	entries = frappe.get_list("Stock Entry", {"item_code": item.item_code})
	for name in entries:
		entry = frappe.get_doc("Stock Entry", name)
		entry.cancel()
		entry.delete()

	item.delete()

	return item.as_dict()
