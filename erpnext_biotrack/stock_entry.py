# -*- coding: utf-8 -*-
# Copyright (c) 2016, Webonyx and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

from .item_utils import make_lot_item
from .biotrackthc.client import create_lot
from frappe import _


def on_submit(doc, method):
	if not doc.convert:
		return doc

	if frappe.flags.in_import or frappe.flags.in_test:
		return

	qty = 0
	if doc.convert_type == _("New Lot"):
		data = []
		for entry in doc.get("items"):
			data.append({
				"barcodeid": entry.item_code,
				"remove_quantity": entry.qty,
			})
			qty += entry.qty

		res = create_lot({"data": data})

		# new lot item
		strain = frappe.get_value("Item", doc.get("items")[0].item_code, "strain")
		item = make_lot_item({
			"item_code": res.get("barcode_id"),
			"barcode": res.get("barcode_id"),
			"item_group": doc.lot_group,
			"default_warehouse": doc.from_warehouse,
			"strain": strain,
		}, qty)

		doc.lot_id = item.item_code
		doc.save()


def get_item_details(doc, method, args=None, for_update=False):
	""" Modify original method data to attach qty and strain """
	return_value = doc.get("_return_value")
	if return_value:
		if return_value.get("actual_qty"):
			return_value["qty"] = return_value.get("actual_qty")

		# assign strain
		return_value["strain"] = frappe.get_value("Item", args.get("item_code"), "strain")
