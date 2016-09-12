from __future__ import unicode_literals
import frappe
from .inventory_room import sync_warehouse
from .client import get_data

@frappe.whitelist()
def sync():
    synced_list = []
    for biotrack_room in get_biotrack_plant_rooms():
        if sync_warehouse(biotrack_room):
            synced_list.append(biotrack_room)

    return len(synced_list)


def get_biotrack_plant_rooms(active=1):
    data = get_data('sync_plant_room', {'active': active})
    return data.get('plant_room') if bool(data.get('success')) else []
