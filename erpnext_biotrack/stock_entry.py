# -*- coding: utf-8 -*-
# Copyright (c) 2016, Webonyx and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from erpnext.stock.doctype.stock_entry.stock_entry import get_warehouse_details


def on_submit(doc, method):
	if frappe.flags.in_import or frappe.flags.in_test:
		return

	from .biotrackthc.client import create_lot, create_product
	if doc.conversion == 'Create Lot':
		create_lot(doc)
	elif doc.conversion == 'Create Product':
		create_product(doc)


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
