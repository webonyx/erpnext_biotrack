from __future__ import unicode_literals
import frappe
from .utils import create_or_update_warehouse
from biotrack_requests import do_request


@frappe.whitelist()
def sync():
	synced_list = []
	for biotrack_room in get_biotrack_inventory_rooms():
		create_or_update_warehouse(biotrack_room, 0, synced_list)

	return len(synced_list)


def get_biotrack_inventory_rooms(active=1):
	data = do_request('sync_inventory_room', {'active': active})
	return data.get('inventory_room') if bool(data.get('success')) else []
