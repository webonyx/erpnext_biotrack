from __future__ import unicode_literals
import frappe
from erpnext_biotrack.utils import create_or_update_warehouse
from client import get_data


@frappe.whitelist()
def sync():
    synced_list = []
    for biotrack_room in get_biotrack_plant_rooms():
        create_or_update_warehouse(biotrack_room, 1, synced_list)

    return len(synced_list)


def get_biotrack_plant_rooms(active=1):
    data = get_data('sync_plant_room', {'active': active})
    return data.get('plant_room') if bool(data.get('success')) else []
