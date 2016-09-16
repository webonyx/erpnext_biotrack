from __future__ import unicode_literals
import frappe
from erpnext import get_default_company
from erpnext_biotrack.config import default_stock_warehouse_name
from .client import get_data


@frappe.whitelist()
def sync():
	synced_list = []
	for biotrack_room in get_biotrack_inventory_rooms():
		if sync_warehouse(biotrack_room, warehouse_type='Inventory Room'):
			synced_list.append(biotrack_room)

	# Bulk Inventory room
	if not frappe.db.exists('Warehouse', {'warehouse_name': default_stock_warehouse_name}):
		under_account = frappe.get_value('BioTrack Settings', None, 'inventory_room_parent_account')
		warehouse = frappe.get_doc({
			'doctype': 'Warehouse',
			'company': get_default_company(),
			'warehouse_name': default_stock_warehouse_name,
			'create_account_under': under_account,
			'warehouse_type': 'Inventory Room'
		})

		warehouse.insert(ignore_permissions=True)
		frappe.db.commit()

	return len(synced_list)


def sync_warehouse(biotrack_data, warehouse_type='Plant Room'):
	name = frappe.get_value(
		'Warehouse', {
			'external_id': biotrack_data.get('roomid'),
			'warehouse_type': warehouse_type
		}
	)

	if name:
		warehouse = frappe.get_doc('Warehouse', name)
		if not frappe.flags.force_sync or False and warehouse.external_transaction_id == biotrack_data.get("transactionid"):
			return False

	else:
		warehouse = frappe.new_doc('Warehouse')
		account = frappe.get_value("BioTrack Settings", None,
								   'plant_room_parent_account' if warehouse_type == 'Plant Room' else 'inventory_room_parent_account')
		warehouse_name = de_duplicate(biotrack_data.get("name"))
		warehouse.update({
			"warehouse_name": warehouse_name,
			'company': get_default_company(),
			'warehouse_type': warehouse_type,
			"create_account_under": account,
			'external_id': biotrack_data.get('roomid'),
		})

	warehouse.update({
		"warehouse_name": biotrack_data.get("name"),
		"external_transaction_id": biotrack_data.get("transactionid"),
		"quarantine": biotrack_data.get("quarantine") or 0,
		"disabled": biotrack_data.get("deleted"),
	})

	warehouse.save(ignore_permissions=True)
	frappe.db.commit()
	return True


def de_duplicate(warehouse_name):
	suffix = " - " + frappe.db.get_value("Company", get_default_company(), "abbr")
	name = warehouse_name + suffix
	original_name = name

	count = 0
	while True:
		if frappe.db.exists("Warehouse", name):
			count += 1
			name = "{0}-{1}".format(original_name, count) + suffix
		else:
			break

	return warehouse_name if count == 0 else "{0}-{1}".format(warehouse_name, count)


def get_default_warehouse():
	name = frappe.db.get_value('Warehouse', {'warehouse_name': default_stock_warehouse_name})
	return frappe.get_doc("Warehouse", name)


def get_biotrack_inventory_rooms(active=1):
	data = get_data('sync_inventory_room', {"active": active})
	return data.get('inventory_room') if bool(data.get('success')) else []
