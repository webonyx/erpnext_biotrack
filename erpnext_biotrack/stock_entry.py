# -*- coding: utf-8 -*-
# Copyright (c) 2016, Webonyx and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

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
		if return_value.get("actual_qty"):
			return_value["qty"] = return_value.get("actual_qty")

		# assign strain
		return_value["strain"] = frappe.get_value("Item", args.get("item_code"), "strain")
