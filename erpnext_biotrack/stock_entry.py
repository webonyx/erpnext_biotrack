# -*- coding: utf-8 -*-
# Copyright (c) 2016, Webonyx and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from erpnext_biotrack.controllers.queries import end_product_sources, inter_product_sources

from .item_utils import make_lot_item, make_item

def before_submit(doc, method):
	"""Item conversion such as Lot creation or Product Conversion"""
	if frappe.flags.in_import or frappe.flags.in_test:
		return

	if not doc.conversion:
		return

	frappe.flags.ignore_external_sync = True

	strain = frappe.get_value("Item", doc.get("items")[0].item_code, "strain")
	from_warehouse = doc.from_warehouse
	qty = 0
	for entry in doc.get("items"):
		qty += entry.qty
		if not from_warehouse and entry.s_warehouse:
			from_warehouse = entry.s_warehouse

	if doc.conversion == 'Create Lot':
		item = make_lot_item({
			"item_group": doc.lot_group,
			"strain": strain,
			"default_warehouse": from_warehouse,
			"disabled": 1,
		}, qty)

		doc.lot_item = item.name

	elif doc.conversion == 'Create Product':
		if doc.product_waste:
			item = make_item(properties={
				"item_group": "Waste",
				"strain": strain,
				"default_warehouse": from_warehouse,
				"disabled": 1,
			}, qty=doc.product_waste)

			doc.waste_item = item.name

		item = make_item(properties={
			"item_name": doc.product_name,
			"item_group": doc.product_group,
			"strain": strain,
			"default_warehouse": from_warehouse,
			"disabled": 1,
		}, qty=doc.product_qty)

		doc.product_item = item.name

	# pass the ball to external adapters such as biotrackthc
	doc.run_method("on_conversion")

	frappe.flags.ignore_external_sync = False

def validate(doc, method):
	if frappe.flags.in_import or frappe.flags.in_test:
		return

	if not doc.conversion:
		return

	item_codes = list(set(item.item_code for item in doc.get("items")))
	item_groups = frappe.db.sql_list("""select distinct item_group from `tabItem`
					where name in ({})""".format(", ".join(["%s"] * len(item_codes))), tuple(item_codes))

	if len(item_groups) > 1:
		frappe.throw(_("Items must be same group. {0} are given.").format(", ".join(item_groups)))

	product_sources = end_product_sources + inter_product_sources
	f = doc.get("items")[0]

	for ste_detail in doc.get("items"):
		if ste_detail.s_warehouse != f.s_warehouse:
			frappe.throw(_("Items must be in same warehouse"))

		if ste_detail.strain != f.strain:
			frappe.throw(_("Items must be same strain"))

		item_group = frappe.get_value("Item", ste_detail.item_code, "item_group")

		if doc.conversion == "Create Lot":
			if doc.lot_group == "Flower Lot" and item_group != "Flower":
				frappe.throw(_("Row {0}: Item must be Flower type").format(ste_detail.idx))

			if doc.lot_group == "Other Plant Material Lot" and item_group != "Other Plant Material":
				frappe.throw(_("Row {0}: Item must be Other Plant Material type").format(ste_detail.idx))

		elif doc.conversion == "Create Product":
			if not item_group in product_sources:
				frappe.throw(_("Row {0}: Invalid item type").format(ste_detail.idx))

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
		return_value["strain"] = frappe.get_value("Item", args.get("item_code"), fieldname="strain")
		source_warehouse = args.get('warehouse')
		filters = {
			"item_code": args.get("item_code"),
			"actual_qty": [">", 0]
		}

		if args.get('warehouse'):
			filters["warehouse"] = args.get('warehouse')

			value = frappe.get_value("Bin", filters=filters, fieldname=["warehouse", "actual_qty"])
			if value:
				source_warehouse, actual_qty = value
				return_value["qty"] = actual_qty

		return_value["s_warehouse"] = source_warehouse
