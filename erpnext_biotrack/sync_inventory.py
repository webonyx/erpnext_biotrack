from __future__ import unicode_literals
import frappe, os
import datetime
from frappe.modules.import_file import read_doc_from_file
from biotrack_requests import do_request
from .utils import get_default_company, make_biotrack_log
from .config import get_default_stock_warehouse

from erpnext_biotrack.doctype.stock_type.stock_type import find_by_code
from erpnext_biotrack.doctype.strain.strain import register_new_strain


@frappe.whitelist()
def sync():
	synced_list = []

	for biotrack_inventory in get_biotrack_inventories():
		if sync_stock(biotrack_inventory, 0):
			synced_list.append(biotrack_inventory)

	return len(synced_list)


def sync_stock(biotrack_inventory, is_plant=0):
	try:
		stock_entry = frappe.get_doc("Stock Entry", {
			"biotrack_stock_external_id": biotrack_inventory.get("id"),
			"biotrack_stock_is_plant": is_plant
		})

		if not stock_entry.biotrack_inventory_sync:
			return False

	except frappe.exceptions.DoesNotExistError:
		posting_datetime = datetime.datetime.fromtimestamp(int(biotrack_inventory.get("sessiontime")))
		posting_date, posting_time = posting_datetime.strftime("%Y-%m-%d %H:%M:%S").split(" ")

		stock_entry = frappe.get_doc({
			"doctype": "Stock Entry",
			"company": get_default_company(),
			"posting_date": posting_date,
			"posting_time": posting_time,
			"biotrack_stock_sync": 1,
			"biotrack_stock_external_id": biotrack_inventory.get("id"),
			"biotrack_stock_is_plant": is_plant,
			"biotrack_stock_transaction_id_original": biotrack_inventory.get("transactionid_original")
		})

	inventory_type = find_by_code(biotrack_inventory.get("inventorytype"))
	if not inventory_type:
		make_biotrack_log(title="Invalid inventory data", status="Error", method="sync_stock",
						  message="inventorytype '%s' is invalid".format(biotrack_inventory.get("inventorytype")),
						  request_data=biotrack_inventory)
		return

	# Warehouse mapping
	if not biotrack_inventory.get("currentroom"):
		from_warehouse = get_default_stock_warehouse()
	else:
		from_warehouse = frappe.get_doc("Warehouse", {"biotrack_room_id": biotrack_inventory.get("currentroom"),
													  "biotrack_warehouse_is_plant_room": is_plant})

	# product (Item) mapping
	if biotrack_inventory.get("productname"):
		item = make_item(biotrack_inventory.get("productname"), {
			"is_stock_item": 1,
			"stock_uom": "G",
			"default_warehouse": from_warehouse.name
		})

	stock_entry.update({
		"biotrack_inventory_type": inventory_type,
		"biotrack_stock_strain": register_new_strain(biotrack_inventory.get("strain")),
		"biotrack_stock_transaction_id": biotrack_inventory.get("transactionid"),
		"from_warehouse": from_warehouse.get("name") if from_warehouse else None,
	})

	stock_entry.save(ignore_permissions=True)
	frappe.db.commit()

	return True


def make_item(item_code, properties=None):
	if frappe.db.exists("Item", item_code):
		uom = frappe.get_doc("Item", item_code)
		if uom.stock_uom != "G":
			uom.stock_uom = "G"
			uom.save()

		return frappe.get_doc("Item", item_code)

	item = frappe.get_doc({
		"doctype": "Item",
		"item_code": item_code,
		"item_name": item_code,
		"description": item_code,
		"item_group": "Products"
	})

	if properties:
		item.update(properties)

	item.insert()

	return item


def get_biotrack_inventories(active=1):
	# f = frappe.get_app_path("erpnext_biotrack", "fixtures/sync_data", "sync_inventory.json")
	# if os.path.exists(f):
	# 	try:
	# 		data = read_doc_from_file(f)
	# 	except IOError:
	# 		print f + " missing"
	# 		return []
	# else:
	# 	result = do_request("sync_inventory", {"active": active})
	# 	data = result.get('inventory') if bool(result.get('success')) else []
	# 	with open(f, "w") as outfile:
	# 		outfile.write(frappe.as_json(data))
	#
	# return data
	data = do_request("sync_inventory", {"active": active})
	return data.get('inventory') if bool(data.get('success')) else []
