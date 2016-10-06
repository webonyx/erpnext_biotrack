from __future__ import unicode_literals
import frappe, datetime
from .client import get_data
from frappe import _
from frappe.utils.data import DATE_FORMAT, flt


@frappe.whitelist()
def sync():
	items = get_biotrack_qa_samples()
	synced = 0

	for item in items:
		if sync_qa_sample(item):
			synced += 1

	return synced, len(items) - synced


def sync_qa_sample(biotrack_item):
	item_code = biotrack_item.get("parentid")

	sample_id = biotrack_item.get("inventoryid")
	quantity = biotrack_item.get("quantity")
	lab_license = biotrack_item.get("lab_license")
	result = biotrack_item.get("result")

	if not frappe.get_value("Item", item_code):
		return False

	supplier_name = frappe.get_value("Supplier", {"license_no": lab_license})
	if not supplier_name:
		return False

	item = frappe.get_doc("Item", item_code)
	if item.test_result:
		return False

	doc = make_sample(item, {"sample_id": sample_id, "quantity": quantity})

	result_map = {-1: "Failed", 0: "Pending", 1: "Passed", 2: "Rejected"}
	doc.update({
		"report_date": datetime.datetime.fromtimestamp(int(biotrack_item.get("sessiontime"))).strftime(DATE_FORMAT),
		"test_result": result_map[result],
		"qa_lab": supplier_name,
	})

	doc.submit()

	# Update item
	frappe.db.set_value("Item", item_code, "test_result", doc.test_result)
	frappe.db.commit()

	return True


def make_sample(item, inventory):
	barcode = inventory.get("sample_id")
	quantity = flt(inventory.get("quantity"))

	if frappe.db.exists("Quality Inspection", {"item_code": item.item_code}):
		doc = frappe.get_doc("Quality Inspection", {"item_code": item.item_code})
	else:
		doc = frappe.new_doc("Quality Inspection")

	doc.update({
		"item_code": item.item_code,
		"item_name": item.item_name,
		"inspection_type": _("In Process"),
		"sample_size": quantity,
		"inspected_by": "Administrator",
		"barcode": barcode
	})

	return doc


def get_biotrack_qa_samples(active=1):
	data = get_data('sync_inventory_qa_sample', {'active': active})
	return data.get('inventory_qa_sample') or []
