from __future__ import unicode_literals
import frappe, os
from client import get_data
from erpnext import get_default_company
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.doctype.stock_reconciliation.stock_reconciliation import get_stock_balance_for
from erpnext_biotrack.utils import make_log, inventories_price_log
from erpnext_biotrack.config import get_default_stock_warehouse
from erpnext_biotrack.erpnext_biotrack.doctype.strain import find_strain
from frappe.utils.data import flt, nowdate, nowtime


@frappe.whitelist()
def sync():
	frappe.flags.in_import = True
	synced_list = []
	result = {
		"error": 0,
		"success": 0
	}

	for biotrack_inventory in get_biotrack_inventories():
		if biotrack_inventory.get("deleted"):
			disable_deleted_item(biotrack_inventory)
			synced_list.append(biotrack_inventory)
			continue

		if sync_inventory(biotrack_inventory, 0, result):
			synced_list.append(biotrack_inventory)

		if result['error'] > 10:
			make_log(status="Error", method="inventories.sync",
					 message="Manually stopped due to errors")
			break

	frappe.flags.in_import = False
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
												   "warehouse_type": 'Inventory Room'})

	# product (Item) mapping
	if biotrack_inventory.get("productname"):
		item_name = biotrack_inventory.get("productname")
	else:
		item_name = " ".join(filter(None, [biotrack_inventory.get("strain"), item_group.name]))

	remaining_quantity = flt(biotrack_inventory.get("remaining_quantity"))
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

		name = barcode
	else:
		name = name[0][0]
		item = frappe.get_doc("Item", name)

	strain = ""
	if biotrack_inventory.get("strain"):
		strain = find_strain(biotrack_inventory.get("strain"))

	# Plant
	# plant = ""
	# if biotrack_inventory.get("plantid"):
	# 	if frappe.db.exists("Plant", {"barcode": biotrack_inventory.get("plantid")}):
	# 		plant = biotrack_inventory.get("plantid")
	#
	# properties["plant"] = plant

	item.update({
		"item_name": item_name,
		"strain": strain,
		"actual_qty": remaining_quantity,
	})

	item.save()

	# Parent
	if biotrack_inventory.get("parentid"):
		for parent_name in biotrack_inventory.get("parentid"):
			if parent_name != item.item_parent and frappe.db.exists("Item", parent_name):
				parent = frappe.get_doc("Item", parent_name)
				parent.append("sub_items", {
					"item_code": barcode,
					"qty": remaining_quantity
				})
				parent.save()
				# properties["item_parent"] = parent_name

	adjust_stock(item, remaining_quantity)

	if remaining_quantity == 0:
		frappe.db.set_value("Item", item.name, "disabled", 1)

	frappe.db.commit()
	result['success'] += 1

	return True


def adjust_stock(item, remaining_quantity):
	posting_date, posting_time = nowdate(), nowtime()
	balance = get_stock_balance_for(item.name, item.default_warehouse, posting_date, posting_time)
	qty = flt(balance["qty"])
	rate = flt(balance["rate"])

	# Material Receipt
	if remaining_quantity > qty:
		make_stock_entry(item_code=item.name, target=item.default_warehouse, qty=remaining_quantity - qty)

	if remaining_quantity < qty:
		create_stock_reconciliation(
			item_code=item.name,
			warehouse=item.default_warehouse,
			qty = remaining_quantity,
			rate=rate if rate > 0 else 1
		)


def create_stock_reconciliation(**args):
	args = frappe._dict(args)
	sr = frappe.new_doc("Stock Reconciliation")
	sr.posting_date = args.posting_date or nowdate()
	sr.posting_time = args.posting_time or nowtime()
	sr.company = args.company or get_default_company()
	sr.append("items", {
		"item_code": args.item_code,
		"warehouse": args.warehouse,
		"qty": args.qty,
		"valuation_rate": args.rate
	})

	sr.submit()
	return sr

def disable_deleted_item(data):
	# todo make log
	barcode = data.get("id")
	frappe.db.set_value("Item", {"barcode": barcode}, "disabled", 1)
	# name = frappe.get_value("Item", {"barcode": barcode, "disabled": 0})

	# if name:
		# entries = frappe.get_list("Stock Entry", {"item_code": name})
		# for name in entries:
		# 	entry = frappe.get_doc("Stock Entry", name)
		# 	entry.cancel()
		# 	entry.delete()
		# frappe.db.set_value("Item", {"barcode": barcode}, "disabled", 1)

def get_biotrack_inventories(active=1):
	return get_data("sync_inventory", {}, 'inventory')
