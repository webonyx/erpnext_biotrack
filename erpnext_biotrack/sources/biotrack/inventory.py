from __future__ import unicode_literals
import frappe, os
from client import get_data
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext_biotrack.utils import make_log, inventories_price_log
from erpnext_biotrack.config import get_default_stock_warehouse
from erpnext_biotrack.erpnext_biotrack.doctype.strain import find_strain

@frappe.whitelist()
def sync():
	synced_list = []
	result = {
		"error": 0,
		"success": 0
	}

	for biotrack_inventory in get_biotrack_inventories():
		if sync_inventory(biotrack_inventory, 0, result):
			synced_list.append(biotrack_inventory)

		if result['error'] > 10:
			make_log(status="Error", method="inventories.sync",
					 message="Manually stopped due to errors")
			break

	return result['success']


def sync_inventory(biotrack_inventory, is_plant=0, result=None):
	barcode = str(biotrack_inventory.get("id"))

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
		f_warehouse = get_default_stock_warehouse()
	else:
		f_warehouse = frappe.get_doc("Warehouse", {"external_id": biotrack_inventory.get("currentroom"),
												   "plant_room": is_plant})

	# product (Item) mapping
	if biotrack_inventory.get("productname"):
		item_name = biotrack_inventory.get("productname")
	else:
		item_name = " - ".join(filter(None, [barcode[-4:], biotrack_inventory.get("strain"), item_group.name]))

	remaining_quantity = float(biotrack_inventory.get("remaining_quantity"))
	name = frappe.db.sql("select name from tabItem where barcode = '{barcode}' or name = '{barcode}'".format(barcode=barcode), as_list=True)
	if not name:
		item = frappe.get_doc({
			"doctype": "Item",
			"item_code": barcode,
			"item_name": item_name,
			"barcode": barcode,
			"is_stock_item": 1,
			"stock_uom": "Gram",
			"item_group": item_group.name,
			"default_warehouse": f_warehouse.name,
		})

		item.insert()
		name = barcode
	else:
		name = name[0][0]
		item = frappe.get_doc("Item", name)

	qty = float(item.get("actual_qty") or 0)

	# Material Receipt
	if remaining_quantity > qty:
		make_stock_entry(item_code=name, target=item.default_warehouse, qty=remaining_quantity - qty)

	properties = {
		"actual_qty": remaining_quantity,
		"is_stock_item": 1 if remaining_quantity > 0 else 0,
	}

	strain = ""
	if biotrack_inventory.get("strain"):
		strain = find_strain(biotrack_inventory.get("strain"))

	if biotrack_inventory.get("parentid"):
		for parent_name in biotrack_inventory.get("parentid"):
			if parent_name != item.item_parent and frappe.db.exists("Item", parent_name):
				parent = frappe.get_doc("Item", parent_name)
				parent.append("sub_items", {
					"item_code": barcode,
					"qty": remaining_quantity
				})
				parent.save()
				properties["item_parent"] = parent_name



	properties["strain"] = strain
	properties["item_name"] = item_name
	item.update(properties)
	item.save()

	frappe.db.commit()
	result['success'] += 1

	return True


def get_inventories_price():
	return inventories_price_log()

def get_biotrack_inventories(active=1):
	return get_data("sync_inventory", {"active": active}, 'inventory')
