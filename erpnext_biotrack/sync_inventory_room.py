from __future__ import unicode_literals
import frappe
from .config import default_stock_warehouse_name
from .utils import create_or_update_warehouse, get_default_company
from biotrack_requests import do_request


@frappe.whitelist()
def sync():
	synced_list = []
	for biotrack_room in get_biotrack_inventory_rooms():
		create_or_update_warehouse(biotrack_room, 0, synced_list)

	# Bulk Inventory room
	if not frappe.db.exists('Warehouse', {'warehouse_name': default_stock_warehouse_name}):
		under_account = frappe.get_value('BioTrack Settings', None, 'inventory_room_parent_account')
		warehouse = frappe.get_doc({
			'doctype': 'Warehouse',
			'company': get_default_company(),
			'warehouse_name': default_stock_warehouse_name,
			'create_account_under': under_account,
			'biotrack_warehouse_is_plant_room': 0
		})

		warehouse.insert(ignore_permissions=True)
		frappe.db.commit()

	return len(synced_list)


def get_biotrack_inventory_rooms(active=1):
	data = do_request('sync_inventory_room', {'active': active})
	return data.get('inventory_room') if bool(data.get('success')) else []
