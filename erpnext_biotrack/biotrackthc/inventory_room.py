from __future__ import unicode_literals
import frappe
from erpnext import get_default_company
from erpnext_biotrack.config import default_stock_warehouse_name
from .client import get_data


@frappe.whitelist()
def sync():
    synced_list = []
    for biotrack_room in get_biotrack_inventory_rooms():
        if sync_warehouse(biotrack_room):
            synced_list.append(biotrack_room)

    # Bulk Inventory room
    if not frappe.db.exists('Warehouse', {'warehouse_name': default_stock_warehouse_name}):
        under_account = frappe.get_value('BioTrack Settings', None, 'inventory_room_parent_account')
        warehouse = frappe.get_doc({
            'doctype': 'Warehouse',
            'company': get_default_company(),
            'warehouse_name': default_stock_warehouse_name,
            'create_account_under': under_account
        })

        warehouse.insert(ignore_permissions=True)
        frappe.db.commit()

    return len(synced_list)


def sync_warehouse(biotrack_data):
    name = frappe.get_value(
        'Warehouse', {
            'external_id': biotrack_data.get('roomid')
        }
    )

    if name:
        warehouse = frappe.get_doc('Warehouse', name)
        if not (frappe.flags.force_sync or False) and warehouse.external_transaction_id == biotrack_data.get(
                "transactionid"):
            return False

    else:
        warehouse = frappe.new_doc('Warehouse')
        account = frappe.get_value("BioTrack Settings", None, "inventory_room_parent_account")
        warehouse.update({
            'company': get_default_company(),
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


def get_default_warehouse():
    name = frappe.db.get_value('Warehouse', {'warehouse_name': default_stock_warehouse_name})
    return frappe.get_doc("Warehouse", name)


def get_biotrack_inventory_rooms(active=1):
    data = get_data('sync_inventory_room', {"active": active})
    return data.get('inventory_room') if bool(data.get('success')) else []
