from __future__ import unicode_literals
import frappe, json
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext_biotrack.biotrackthc.qa_sample import make_sample
from erpnext_biotrack.item_utils import get_item_values
from frappe.utils import get_fullname

from .client import get_data
from erpnext_biotrack.config import get_default_stock_warehouse
from erpnext_biotrack.traceability_system.doctype.strain import find_strain
from frappe.utils.data import flt, nowdate, nowtime, now, cint


@frappe.whitelist()
def sync():
	"""Manual execute: bench execute erpnext_biotrack.biotrackthc.inventory.sync"""
	success = 0
	sync_time = now()
	samples = []

	for inventory in get_biotrack_inventories():
		if inventory.get("is_sample"):
			samples.append(inventory)
			continue

		if sync_item(inventory):
			success += 1

	disable_deleted_items(sync_time)
	syn_samples(samples)

	return success, 0


def sync_item(data):
	barcode = str(data.get("id"))
	remaining_quantity = flt(data.get("remaining_quantity"))
	name = None

	item_values = get_item_values(barcode, ["name", "transaction_id"])
	if item_values:
		name, transaction_id = item_values
		if not (frappe.flags.force_sync or False) and transaction_id == data.get("transactionid"):
			frappe.db.set_value("Item", name, "bio_last_sync", now(), update_modified=False)
			return False

	# inventory type
	item_group = find_item_group(data)
	warehouse = find_warehouse(data)
	current_remaining_quantity = 0

	# product (Item) mapping
	if data.get("productname"):
		item_name = data.get("productname")
	else:
		item_name = " ".join(filter(None, [data.get("strain"), item_group.name]))

	if not name:
		item_code = barcode
		item = frappe.get_doc({
			"doctype": "Item",
			"item_code": item_code,
			"item_name": item_name,
			"bio_barcode": barcode,
			"is_stock_item": 1,
			"stock_uom": "Gram",
			"item_group": item_group.name,
			"default_warehouse": warehouse.name,
		})
	else:
		item = frappe.get_doc("Item", name)
		current_remaining_quantity = item.bio_remaining_quantity

	strain = ""
	if data.get("strain"):
		strain = find_strain(data.get("strain"))

	# Post task will do on biotrack_after_sync hook
	parent_ids = data.get("parentid")
	plant_ids = data.get("plantid")
	if not item.is_lot_item and (parent_ids or plant_ids):
		item.set("linking_data", json.dumps({"parent_ids": parent_ids, "plant_ids": plant_ids}))

	item.update({
		"item_name": item_name,
		"bio_barcode": barcode,
		"strain": strain,
		"bio_remaining_quantity": remaining_quantity,
		"transaction_id": data.get("transactionid"),
		"bio_last_sync": now(),
		"disabled": 1 if remaining_quantity == 0 else 0,
	})

	item.flags.ignore_links = True
	item.save()

	# adjust_stock
	if item.is_stock_item:
		if remaining_quantity > current_remaining_quantity:
			make_stock_entry(item_code=item.name, target=item.default_warehouse, qty=remaining_quantity - current_remaining_quantity)

		# Consider to not modified down item's balance because it's hard to figure out the correct warehouse and its balance to deduct
		# elif remaining_quantity < current_remaining_quantity:
		# 	posting_date, posting_time = nowdate(), nowtime()
		# 	balance = get_stock_balance_for(item.name, item.default_warehouse, posting_date, posting_time)
		#
		# 	if balance["qty"] >= remaining_quantity:
		# 		make_stock_entry(item_code=item.name, source=item.default_warehouse,
		# 					 qty=current_remaining_quantity - remaining_quantity)

	# Disable Usable Marijuana item does not have product name
	if not data.get("productname") and item_group.external_id == 28:
		frappe.db.set_value("Item", item.name, "disabled", 1)
		log_invalid_item(item)

	frappe.db.commit()

	return True


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




def find_warehouse(data):
	if not data.get("currentroom"):
		warehouse = get_default_stock_warehouse()
	else:
		warehouse = frappe.get_doc("Warehouse", {"external_id": data.get("currentroom")})

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
		"update tabItem set `bio_remaining_quantity` = 0, `disabled` = 1 where transaction_id IS NOT NULL and (`bio_last_sync` IS NULL or `bio_last_sync` < %(bio_last_sync)s)",
		{"bio_last_sync": sync_time})


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


def get_biotrack_inventories(active=1, client=None):
	return get_data("sync_inventory", {"active": active}, 'inventory', client=client)
