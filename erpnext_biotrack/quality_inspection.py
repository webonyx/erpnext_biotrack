# -*- coding: utf-8 -*-
# Copyright (c) 2016, Webonyx and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from erpnext.stock.dashboard.item_dashboard import get_data
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry


def on_submit(doc, method):
	"""Handle sample item"""
	if frappe.flags.in_import or frappe.flags.in_test:
		return

	if not doc.is_sample:
		return

	valid_groups = [
		_('Flower Lot'),
		_('CO2 Hash Oil'),
		_('Food Grade Solvent Extract'),
		_('Hydrocarbon Wax'),
		_('Marijuana Extract for Inhalation'),
		_('Solid Marijuana Infused Edible'),
		_('Usable Marijuana')
	]

	item_group = frappe.get_value("Item", doc.item_code, "item_group")
	if not _(item_group) in valid_groups:
		frappe.throw(
			_("Item is not eligible for making sample."),
			title="Invalid Item")

	# Stock update had been handled by delivery_note
	if doc.inspection_type == "Outgoing" and doc.delivery_note_no:
		return

	inventories = get_data(item_code=doc.item_code)
	source_warehouse = None
	actual_qty = 0

	for inventory in inventories:
		if inventory.actual_qty > actual_qty:
			actual_qty = inventory.actual_qty

		if inventory.actual_qty >= doc.sample_size:
			source_warehouse = inventory.warehouse
			break

	if not source_warehouse:
		frappe.throw(
			_("Qty is not available for provided sample size. Qty remaining <strong>{0}</strong>.").format(actual_qty),
			title="Insufficient Stock")

	make_stock_entry(item_code=doc.item_code, source=source_warehouse, qty=doc.sample_size)

def on_validate(doc, method):
	if frappe.flags.in_import or frappe.flags.in_test:
		return

	if doc.is_sample:
		return
