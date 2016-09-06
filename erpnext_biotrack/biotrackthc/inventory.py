from __future__ import unicode_literals
import frappe, os
from erpnext import get_default_company
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.doctype.stock_reconciliation.stock_reconciliation import get_stock_balance_for
from erpnext_biotrack.item_utils import get_item_values
from erpnext_biotrack.sources.biotrack.client import get_data
from erpnext_biotrack.config import get_default_stock_warehouse
from erpnext_biotrack.erpnext_biotrack.doctype.strain import find_strain
from frappe.utils.data import flt, nowdate, nowtime, now


@frappe.whitelist()
def sync():
	frappe.flags.in_import = True
	success = 0
	sync_time = now()

	for biotrack_inventory in get_biotrack_inventories():
		if sync_item(biotrack_inventory, sync_time):
			success += 1

	disable_deleted_items(sync_time)
	frappe.flags.in_import = False

	return success, 0


def sync_item(biotrack_inventory, sync_time=None):
	barcode = str(biotrack_inventory.get("id"))
	remaining_quantity = flt(biotrack_inventory.get("remaining_quantity"))
	name = None

	if not sync_time:
		sync_time = now()

	item_values = get_item_values(barcode, ["name", "transaction_id"])
	if item_values:
		name, transaction_id = item_values
		if not frappe.flags.force_sync or False and transaction_id == biotrack_inventory.get("transactionid"):
			frappe.db.set_value("Item", name, "last_sync", sync_time, update_modified=False)
			return False

	# inventory type
	item_group = find_item_group(biotrack_inventory)
	warehouse = find_warehouse(biotrack_inventory)

	# product (Item) mapping
	if biotrack_inventory.get("productname"):
		item_name = biotrack_inventory.get("productname")
	else:
		item_name = " ".join(filter(None, [biotrack_inventory.get("strain"), item_group.name]))

	if not name:
		item = frappe.get_doc({
			"doctype": "Item",
			"item_code": barcode,
			"item_name": item_name,
			"barcode": barcode,
			"is_stock_item": 1,
			"stock_uom": "Gram",
			"item_group": item_group.name,
			"default_warehouse": warehouse.name,
		})
	else:
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
		"transaction_id": biotrack_inventory.get("transactionid"),
		"last_sync": now(),
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
			qty=remaining_quantity,
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


def find_warehouse(data):
	if not data.get("currentroom"):
		warehouse = get_default_stock_warehouse()
	else:
		warehouse = frappe.get_doc("Warehouse", {"external_id": data.get("currentroom"),
												 "warehouse_type": 'Inventory Room'})
	return warehouse


def find_item_group(data):
	item_group = frappe.get_doc("Item Group", {"external_id": data.get("inventorytype"),
											   "parent_item_group": "WA State Classifications"})
	if not item_group:
		raise ImportError("Data error, inventorytype '{0}' was not found. Please update database from state.".format(
			data.get("inventorytype")))

	return item_group


def disable_deleted_items(last_sync=None):
	if not last_sync:
		last_sync = now()

	return frappe.db.sql(
		"update tabItem set `actual_qty` = 0, `disabled` = 1 where transaction_id IS NOT NULL and (`last_sync` IS NULL or `last_sync` < %(last_sync)s)",
		{"last_sync": last_sync})


def get_biotrack_inventories(active=1):
	return get_data("sync_inventory", {"active": active}, 'inventory')
