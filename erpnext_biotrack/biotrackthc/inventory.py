from __future__ import unicode_literals
import frappe, json
from erpnext import get_default_company
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.doctype.stock_reconciliation.stock_reconciliation import get_stock_balance_for
from erpnext_biotrack.biotrackthc.plant import get_normalized as get_normalized_plants
from erpnext_biotrack.biotrackthc.qa_sample import make_sample
from erpnext_biotrack.item_utils import get_item_values
from frappe.utils import get_fullname

from .client import get_data
from erpnext_biotrack.config import get_default_stock_warehouse
from erpnext_biotrack.erpnext_biotrack.doctype.strain import find_strain
from frappe.utils.data import flt, nowdate, nowtime, now, cint


@frappe.whitelist()
def sync():
	"""Manual execute: bench execute erpnext_biotrack.biotrackthc.inventory.sync"""
	success = 0
	sync_time = now()
	samples = []

	data = normalize(get_biotrack_inventories())
	plant_data = get_normalized_plants()

	for _, inventory in data.items():
		# filter to keep available parent only
		ids = inventory.get("parentid") or []
		parent_ids = []
		if ids:
			for key in (inventory.get("parentid") or []):
				if key in data:
					parent_ids.append(key)

			# lookup again database
			if not parent_ids:
				parent_ids = [r[0] for r in frappe.get_list("Item", filters=[["barcode", "in", ids]], as_list=True)]

		# plants filter
		ids = inventory.get("plantid") or []
		plant_ids = []
		if ids:
			for key in (inventory.get("plantid") or []):
				if key in plant_data:
					plant_ids.append(key)

			# lookup again database
			if not plant_ids:
				plant_ids = [r[0] for r in frappe.get_list("Plant", filters=[["name", "in", ids]], as_list=True)]

		inventory["parentid"] = parent_ids
		inventory["plantid"] = plant_ids

		if inventory.get("is_sample") and parent_ids:
			samples.append(inventory)
			continue

		if sync_item(inventory):
			success += 1

	disable_deleted_items(sync_time)
	syn_samples(samples)

	return success, 0


def sync_item(biotrack_inventory):
	barcode = str(biotrack_inventory.get("id"))
	remaining_quantity = flt(biotrack_inventory.get("remaining_quantity"))
	name = None

	item_values = get_item_values(barcode, ["name", "transaction_id"])
	if item_values:
		name, transaction_id = item_values
		if not (frappe.flags.force_sync or False) and transaction_id == biotrack_inventory.get("transactionid"):
			frappe.db.set_value("Item", name, "last_sync", now(), update_modified=False)
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
		item_code = barcode
		item = frappe.get_doc({
			"doctype": "Item",
			"item_code": item_code,
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

	# Post task will do on biotrack_after_sync hook
	parent_ids = biotrack_inventory.get("parentid")
	plant_ids = biotrack_inventory.get("plantid")
	if parent_ids or plant_ids:
		item.set("linking_data", json.dumps({"parent_ids": parent_ids, "plant_ids": plant_ids}))

	item.update({
		"item_name": item_name,
		"strain": strain,
		"actual_qty": remaining_quantity,
		"transaction_id": biotrack_inventory.get("transactionid"),
		"last_sync": now(),
		"disabled": 1 if remaining_quantity == 0 else 0,
	})

	item.save()

	if remaining_quantity and item.is_stock_item:
		adjust_stock(item, remaining_quantity)

	# Disable Usable Marijuana item does not have product name
	if not biotrack_inventory.get("productname") and item_group.external_id == 28:
		frappe.db.set_value("Item", item.name, "disabled", 1)
		log_invalid_item(item)

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
			item_name=item.item_name,
			warehouse=item.default_warehouse,
			qty=remaining_quantity,
			rate=rate if rate > 0 else 1
		)


def syn_samples(samples):
	for inventory in samples:
		parent_ids = inventory.get("parentid") or []
		if not parent_ids:
			continue

		item_code = parent_ids[0]
		values = get_item_values(item_code, ["name", "test_result", "item_name"])
		if values:
			name, test_result, item_name = values
			if test_result:
				continue # already synced

			item = frappe.get_doc("Item", name)
			item.sample_id = inventory.get("barcode")
			item.save()

			quality_inspection = make_sample(item, inventory.get("remaining_quantity"))
			quality_inspection.flags.ignore_mandatory = True
			quality_inspection.save()

			frappe.db.commit()

		else:
			continue # not found related item



def create_stock_reconciliation(**args):
	args = frappe._dict(args)
	sr = frappe.new_doc("Stock Reconciliation")
	sr.posting_date = args.posting_date or nowdate()
	sr.posting_time = args.posting_time or nowtime()
	sr.company = args.company or get_default_company()
	sr.append("items", {
		"item_code": args.item_code,
		"item_name": args.item_name,
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


def disable_deleted_items(sync_time=None):
	if not sync_time:
		sync_time = now()

	return frappe.db.sql(
		"update tabItem set `actual_qty` = 0, `disabled` = 1 where transaction_id IS NOT NULL and (`last_sync` IS NULL or `last_sync` < %(last_sync)s)",
		{"last_sync": sync_time})


def log_invalid_item(item):
	frappe.db.sql("""delete from `tabCommunication`
					where
						reference_doctype=%s and reference_name=%s
						and communication_type='Comment'
						and comment_type='Cancelled'""", ("Item", item.name))

	frappe.get_doc({
		"doctype": "Communication",
		"communication_type": "Comment",
		"comment_type": "Cancelled",
		"reference_doctype": "Item",
		"reference_name": item.name,
		"subject": item.item_name,
		"full_name": get_fullname(item.owner),
		"reference_owner": item.owner,
		# "link_doctype": "Item",
		# "link_name": item.name
	}).insert(ignore_permissions=True)


def normalize(data):
	normalized = {}
	for inventory in data:
		normalized[inventory.get("id")] = inventory

	return normalized


def get_biotrack_inventories(active=1):
	return get_data("sync_inventory", {"active": active}, 'inventory')
