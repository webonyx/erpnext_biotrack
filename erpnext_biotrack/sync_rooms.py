from __future__ import unicode_literals
import frappe
from frappe.exceptions import DoesNotExistError
from .utils import get_default_company, skip_on_duplicating
from biotrack_requests import do_request

def sync():
	return sync_with_check(get_biotrack_rooms())

def sync_inventory():
	return sync_with_check(get_biotrack_inventory_rooms(), False)

def sync_with_check(biotrack_rooms, is_plant_room = True):
	synced = []
	for biotrack_room in biotrack_rooms:
		if skip_on_duplicating():
			if frappe.db.exists({'doctype': 'Warehouse', 'warehouse_name': biotrack_room.get("name")}):
				continue

			biotrack_room['is_plant_room'] = is_plant_room
			create_room(biotrack_room, synced)

	return len(synced)

def create_room(biotrack_room, list):
	company = get_default_company()

	try:
		warehouse = frappe.get_doc('Warehouse', {'biotrack_room_id': biotrack_room.get("roomid")})
		if not warehouse.biotrack_warehouse_sync:
			return
	except DoesNotExistError as e:
		warehouse = frappe.get_doc({'doctype':'Warehouse'})
		warehouse.set('biotrack_warehouse_sync', 1)
		warehouse.set('company', company)

	stock_group = frappe.db.get_value("Account", {"account_type": "Stock", "is_group": 1, "company": company})
	if stock_group:
		warehouse.update({
			"warehouse_name": biotrack_room.get("name"),
			"biotrack_room_id": biotrack_room.get("roomid"),
			"biotrack_warehouse_location_id": biotrack_room.get("location"),
			"biotrack_warehouse_transaction_id": biotrack_room.get("transactionid"),
			"biotrack_warehouse_transaction_id_original": biotrack_room.get("transactionid_original"),
			"biotrack_warehouse_is_plant_room": biotrack_room.get("is_plant_room") or 0,
			"biotrack_warehouse_quarantine": biotrack_room.get("quarantine") or 0
		})

		warehouse.flags.ignore_permissions = True
		warehouse.save()
		list.append(warehouse.biotrack_room_id)

		frappe.db.commit()


def get_biotrack_rooms():
	data = do_request('sync_plant_room', {'active': 1})
	return data.get('plant_room') if bool(data.get('success')) else []


def get_biotrack_inventory_rooms():
	data = do_request('sync_inventory_room', {'active': 1})
	return data.get('inventory_room') if bool(data.get('success')) else []
