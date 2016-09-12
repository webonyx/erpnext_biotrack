from __future__ import unicode_literals
import frappe, datetime
from .client import get_data
from frappe import _
from frappe.utils.data import DATE_FORMAT

@frappe.whitelist()
def sync():
	items = get_biotrack_qa_samples()
	for item in items:
		sync_qa_sample(item)

	return len(items)


def sync_qa_sample(biotrack_item):
	external_id = biotrack_item.get("inventoryid")
	barcode = biotrack_item.get("parentid")
	lab_license = biotrack_item.get("lab_license")
	result = biotrack_item.get("result")

	inspect_name = frappe.get_value("Quality Inspection", {"external_id": external_id})
	if inspect_name:
		return

	item_name = frappe.get_value("Item", {"barcode": barcode})
	if not item_name:
		return

	supplier_name = frappe.get_value("Supplier", {"license_no": lab_license})
	if not supplier_name:
		return

	result_map = {-1: "Failed", 0: "Pending", 1: "Passed", 2: "Rejected"}
	doc = frappe.get_doc({
		"doctype": "Quality Inspection",
		"item_code": item_name,
		"inspection_type": _("In Process"),
		"sample_size": biotrack_item.get("quantity"),
		"report_date": datetime.datetime.fromtimestamp(int(biotrack_item.get("sessiontime"))).strftime(DATE_FORMAT),
		"inspected_by": "Administrator",
		"verified_by": supplier_name,
		"qa_lab": supplier_name,
		"external_id": external_id,
		"test_result": result_map[result],
	})

	doc.submit()

	frappe.db.commit()



def get_biotrack_qa_samples(active=1):
	data = get_data('sync_inventory_qa_sample', {'active': active})
	return data.get('inventory_qa_sample') or []
