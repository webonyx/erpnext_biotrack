from __future__ import unicode_literals
import frappe, datetime
from .client import get_data
from frappe import _
from frappe.utils.data import DATE_FORMAT


@frappe.whitelist()
def sync():
    items = get_biotrack_qa_samples()
    synced = 0

    for item in items:
        if sync_qa_sample(item):
            synced += 1

    return synced, len(items) - synced


def sync_qa_sample(biotrack_item):
    sample_id = biotrack_item.get("inventoryid")
    barcode = biotrack_item.get("parentid")
    lab_license = biotrack_item.get("lab_license")
    result = biotrack_item.get("result")

    inspect_name = frappe.get_value("Quality Inspection", {"sample_code": sample_id})
    if inspect_name:
        return False

    sample = frappe.get_value("Item", {"barcode": sample_id},["name", "item_name"])
    if not sample:
        return False

    parent = frappe.get_value("Item", {"barcode": barcode})
    if not parent:
        return False

    item_code, item_name = sample
    supplier_name = frappe.get_value("Supplier", {"license_no": lab_license})
    if not supplier_name:
        return False

    result_map = {-1: "Failed", 0: "Pending", 1: "Passed", 2: "Rejected"}
    doc = frappe.get_doc({
        "doctype": "Quality Inspection",
        "item_code": item_code,
        "item_name": item_name,
        "inspection_type": _("In Process"),
        "sample_size": biotrack_item.get("quantity"),
        "report_date": datetime.datetime.fromtimestamp(int(biotrack_item.get("sessiontime"))).strftime(DATE_FORMAT),
        "inspected_by": "Administrator",
        "verified_by": supplier_name,
        "qa_lab": supplier_name,
        "sample_code": item_code,
        "test_result": result_map[result],
    })

    doc.submit()

    # Update item
    frappe.db.set_value("Item", parent, "sample", item_code)
    frappe.db.set_value("Item", parent, "test_result", doc.test_result)
    frappe.db.set_value("Item", item_code, "is_sample", 1)

    frappe.db.commit()

    return True


def get_biotrack_qa_samples(active=1):
    data = get_data('sync_inventory_qa_sample', {'active': active})
    return data.get('inventory_qa_sample') or []
