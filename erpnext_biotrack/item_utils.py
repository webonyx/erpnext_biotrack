# -*- coding: utf-8 -*-
# Copyright (c) 2016, Webonyx and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import json
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


def make_item(**args):
	args = frappe._dict(args)

	if args.barcode:
		frappe.flags.in_import = True  # ignore custom validate and after_insert hooks

	item = frappe.new_doc("Item")
	properties = frappe._dict(args.properties) or frappe._dict()
	properties['item_name'] = properties.item_name or " ".join(filter(None, [properties.strain, properties.item_group]))

	if args.barcode:
		properties['item_code'] = args.barcode
		properties['barcode'] = args.barcode

	item.update(properties)
	item.insert()

	if args.qty:
		make_stock_entry(item_code=item.item_code, target=item.default_warehouse, qty=args.qty)

	frappe.flags.in_import = False

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
		"parent_item": parent.name,
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


def get_item_values(barcode, fields="name"):
	if isinstance(fields, basestring):
		fl = fields
	else:
		fl = ["`" + f + "`" for f in fields]
		fl = ", ".join(fl)

	result = frappe.db.sql(
		"select {0} from tabItem where `name` = %(barcode)s or `barcode` =  %(barcode)s".format(fl),
		{"barcode": barcode}, as_list=True)

	return result[0] if result else None


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


def remove_certificate_on_trash_file(file, method):
	if file.attached_to_name and file.attached_to_doctype == "Item":
		item = frappe.get_doc("Item", file.attached_to_name)
		if (item.certificate == file.file_url):
			item.certificate = None
			item.save()


def item_linking_correction():
	"""For biotrack_after_sync Hook"""

	for name in frappe.get_all("Item", filters=["linking_data IS NOT NULL"]):
		item = frappe.get_doc("Item", name)
		linking_data = json.loads(item.linking_data)

		if linking_data.get("parent_ids"):
			parent_name = linking_data.get("parent_ids")[0]

			# consider to not make circular linking
			# parent = frappe.get_doc("Item", parent_name)
			# parent.append("sub_items", {
			# 	"item_code": parent_name,
			# 	"qty": item.actual_qty
			# })
			# parent.save()

			if frappe.db.exists("Item", parent_name):
				frappe.db.set_value("Item", item.name, "parent_item", parent_name)

		if linking_data.get("plant_ids"):
			plant_name = linking_data.get("plant_ids")[0]
			if frappe.db.exists("Plant", plant_name):
				frappe.db.set_value("Item", item.name, "plant", plant_name)

		frappe.db.set_value("Item", item.name, "linking_data", None)


def qa_result_population():
	"""Call from biotrack_after_sync"""
	for name in frappe.get_all("Item", filters={"test_result": "Passed", "inspection_required": 0}):
		qa_result_pull(name)


def qa_result_pull(name):
	item = frappe.get_doc("Item", name)
	data = biotrackthc_call("inventory_qa_check", {"sample_id": item.sample_id})

	if data.get("result") != 1:
		result_map = {-1: "Failed", 0: "Pending", 1: "Passed", 2: "Rejected"}
		frappe.db.set_value("Item", name, "test_result", result_map[data.get("result")])
		return False # Failed

	for d in data.get("test") or []:
		for key, val in d.items():
			if key == 'type':
				continue

			item.get("quality_parameters").append(frappe.get_doc({
				"doctype": "Item Quality Inspection Parameter",
				"parentfield": 'quality_parameters',
				"specification": key,
				"value": val
			}))

	item.inspection_required = 1
	item.save()
	frappe.db.commit()


def delete_item(name):
	"""Permanently Item and related Stock entries"""
	item = frappe.get_doc("Item", name)

	for name in frappe.get_list("Stock Entry", {"item_code": item.item_code}):
		doc = frappe.get_doc("Stock Entry", name)
		if doc.docstatus == 1:
			doc.cancel()

		doc.delete()

	for name in frappe.get_all("Delivery Note", {"item_code": item.item_code}):
		doc = frappe.get_doc("Delivery Note", name)
		if doc.docstatus == 1:
			doc.cancel()
		doc.delete()

	item.delete()

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
