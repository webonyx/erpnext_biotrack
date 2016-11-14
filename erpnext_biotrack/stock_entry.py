# -*- coding: utf-8 -*-
# Copyright (c) 2016, Webonyx and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from erpnext.stock.doctype.stock_entry.stock_entry import get_warehouse_details
from .item_utils import make_lot_item, make_item

def on_submit(doc, method):
	if frappe.flags.in_import or frappe.flags.in_test:
		return

	frappe.flags.ignore_external_sync = True

	if doc.conversion == 'Create Lot':
		item = _create_lot(doc)
		doc.lot_item = item.name

	elif doc.conversion == 'Create Product':
		if doc.product_waste:
			waste = make_item(properties={
				"item_name": "Waste",
				"item_group": "Waste",
				"default_warehouse": doc.from_warehouse,
			}, qty=doc.product_waste)

			doc.waste_item = waste.name

		product = make_item(properties={
			"item_name": doc.product_name or doc.product_group,
			"item_group": doc.product_group,
			"default_warehouse": doc.from_warehouse,
		}, qty=doc.product_qty)

		doc.product_item = product.name

	doc.flags.ignore_validate_update_after_submit = True
	doc.save()

	doc.run_method('after_conversion')

	frappe.flags.ignore_external_sync = False

def _create_lot(doc):
	qty = 0
	for entry in doc.get("items"):
		qty += entry.qty

	strain = frappe.get_value("Item", doc.get("items")[0].item_code, "strain")
	return make_lot_item({
		"item_group": doc.lot_group,
		"default_warehouse": doc.from_warehouse,
		"strain": strain,
	}, qty)


def on_validate(doc, method):
	if frappe.flags.in_import or frappe.flags.in_test:
		return

	if not doc.conversion:
		return

	missing = []
	if not doc.lot_group:
		missing.append("lot_group")

	if not missing:
		return

	raise frappe.MandatoryError('[{doctype}, {name}]: {fields}'.format(
		fields=", ".join((each for each in missing)),
		doctype=doc.doctype,
		name=doc.name))

def get_item_details(doc, method, args=None, for_update=False):
	""" Modify original method data to attach qty and strain """
	return_value = doc.get("_return_value")
	if return_value:
		default_warehouse, strain = frappe.get_value("Item", args.get("item_code"), ["default_warehouse", "strain"])
		if not args.get('warehouse') or args.get('warehouse') != default_warehouse:
			# auto correct source warehouse by default one
			args["warehouse"] = return_value["s_warehouse"] = default_warehouse

			# try again
			stock_and_rate = get_warehouse_details(args) or {}
			return_value.update(stock_and_rate)

		if return_value.get("actual_qty"):
			return_value["qty"] = return_value.get("actual_qty")

		# assign strain
		return_value["strain"] = strain
