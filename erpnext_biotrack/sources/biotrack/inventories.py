from __future__ import unicode_literals
import frappe, os
import datetime
import json
from client import get_data
from erpnext_biotrack.utils import get_default_company, make_log
from erpnext_biotrack.config import get_default_stock_warehouse
from erpnext_biotrack.erpnext_biotrack.doctype.strain import register_new_strain


@frappe.whitelist()
def sync():
	synced_list = []
	result = {
		"error": 0,
		"success": 0
	}

	for biotrack_inventory in get_biotrack_inventories():
		if sync_stock(biotrack_inventory, 0, result):
			synced_list.append(biotrack_inventory)

		if result['error'] > 10:
			make_log(status="Error", method="inventories.sync",
					 message="Manually stopped due to errors")
			break

	return result['success']


def sync_stock(biotrack_inventory, is_plant=0, result=None):
	try:
		stock_entry = frappe.get_doc("Stock Entry", {
			"external_id": biotrack_inventory.get("id"),
			"is_plant": is_plant
		})

		if not stock_entry.wa_state_compliance_sync:
			return False

	except frappe.exceptions.DoesNotExistError:
		posting_datetime = datetime.datetime.fromtimestamp(int(biotrack_inventory.get("sessiontime")))
		posting_date, posting_time = posting_datetime.strftime("%Y-%m-%d %H:%M:%S").split(" ")

		stock_entry = frappe.get_doc({
			"doctype": "Stock Entry",
			"company": get_default_company(),
			"posting_date": posting_date,
			"posting_time": posting_time,
			"wa_state_compliance_sync": 1,
			"external_id": biotrack_inventory.get("id"),
			"is_plant": is_plant,
		})

	# inventory type
	item_group = frappe.get_doc("Item Group", {"external_id": biotrack_inventory.get("inventorytype"),
											   "parent_item_group": "WA State Classifications"})
	if not item_group:
		make_log(title="Invalid inventory type", status="Error", method="sync_stock",
						  message="inventorytype '{0}' is not found".format(biotrack_inventory.get("inventorytype")),
						  request_data=biotrack_inventory)
		return

	# Warehouse mapping
	if not biotrack_inventory.get("currentroom"):
		from_warehouse = get_default_stock_warehouse()
	else:
		from_warehouse = frappe.get_doc("Warehouse", {"external_id": biotrack_inventory.get("currentroom"),
													  "plant_room": is_plant})

	stock_entry.update({
		"external_transaction_id": biotrack_inventory.get("transactionid"),
		"from_warehouse": from_warehouse.get("name") if from_warehouse else None,
	})

	# product (Item) mapping
	if biotrack_inventory.get("productname"):
		item_code = biotrack_inventory.get("productname")
	else:
		item_code = "{0} - {1}".format(biotrack_inventory.get("strain"), item_group.name)

	item = make_item(item_code, {
		"is_stock_item": 1,
		"stock_uom": "Gram",
		"item_group": item_group.name,
		"default_warehouse": from_warehouse.name
	})

	add_item_detail(stock_entry, item, biotrack_inventory)

	try:
		stock_entry.submit()
	except frappe.exceptions.ValidationError as e:
		result['error'] += 1
		make_log(status="Error", method="inventories.sync_stock",
						  message="{}: {}\n{}".format(type(e).__name__, e.message, json.dumps(biotrack_inventory)),
						  request_data=biotrack_inventory)

 	frappe.db.commit()
	result['success'] += 1

	return True


def add_item_detail(stock_entry, item, biotrack_inventory):
	stock_entry_detail = None
	qty = float(biotrack_inventory.get("remaining_quantity"))

	for item_detail in stock_entry.get("items"):
		if item_detail.item_code == item.item_code:
			stock_entry_detail = item_detail
			break

	if not stock_entry_detail:
		stock_entry_detail = frappe.get_doc({
			"doctype": "Stock Entry Detail",
			"barcode": biotrack_inventory.get("id"),
			"strain": register_new_strain(biotrack_inventory.get("strain")),
			"item_code": item.item_code,
			"qty": qty,
			"actual_qty": qty,
			"conversion_factor": 1,
			"uom": item.stock_uom,
			"parentfield": "items",
		})

		stock_entry.get("items").append(stock_entry_detail)
	else:
		stock_entry_detail.update({
			"qty": qty,
			"actual_qty": qty,
		})


def make_item(item_code, properties=None):
	item_code = str(item_code).strip()
	if frappe.db.exists("Item", item_code):
		item = frappe.get_doc("Item", item_code)
	else:
		item = frappe.get_doc({
			"doctype": "Item",
			"item_code": item_code,
			"item_name": item_code,
			"description": item_code,
		})

	if properties:
		item.update(properties)

	item.save()

	return item


def get_biotrack_inventories(active=1):
	return get_data("sync_inventory", {"active": active}, 'inventory')
