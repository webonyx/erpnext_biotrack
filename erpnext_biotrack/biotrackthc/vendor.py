from __future__ import unicode_literals
import frappe
from erpnext_biotrack.sources.biotrack.client import get_data
from frappe import _
from frappe.exceptions import DoesNotExistError
from frappe.utils import cstr
from frappe.utils.nestedset import get_root_of


def sync():
	success = 0
	for biotrack_customer in get_biotrack_vendors():
		if create_or_update_customer(biotrack_customer):
			success += 1

	return success, 0


def create_or_update_customer(biotrack_customer):
	try:
		customer = frappe.get_doc('Customer', biotrack_customer.get("name"))
		if not frappe.flags.force_sync or False and customer.get("external_transaction_id") == biotrack_customer.get(
				"transactionid"):
			return False

	except DoesNotExistError:
		customer = frappe.get_doc({
			"doctype": "Customer",
			"customer_name": biotrack_customer.get("name"),
			"territory": get_root_of("Territory"),
			"customer_type": _("Company")
		})

	customer_group = detect_group(biotrack_customer)
	customer.update({
		"customer_group": customer_group.name if customer_group else None,
		"territory": get_root_of("Territory"),
		"ubi": biotrack_customer.get("ubi"),
		"license_no": biotrack_customer.get("location"),
		"external_transaction_id": biotrack_customer.get("transactionid")
	})

	customer.flags.ignore_mandatory = True
	customer.save()

	if customer:
		create_customer_address(customer, biotrack_customer)

	frappe.db.commit()
	return True


def detect_group(biotrack_customer):
	producer, processor, retail, medical = [
		int(biotrack_customer.get('producer')),
		int(biotrack_customer.get('processor')),
		int(biotrack_customer.get('retail')),
		int(biotrack_customer.get('medical')),
	]

	name = None
	if producer and processor:
		name = _('Producer/Processor')
	elif retail and medical:
		name = _('Retailer/Medical')
	elif producer:
		name = _('Producer')
	elif processor:
		name = _('Processor')
	elif retail:
		name = _('Retailer')

	if name:
		return get_or_create_group(name)


def get_or_create_group(name):
	try:
		group = frappe.get_doc('Customer Group', name)
	except DoesNotExistError as e:
		group = frappe.get_doc({'doctype': 'Customer Group', 'name': name, 'customer_group_name': name, 'is_group': 0,
								'parent_customer_group': _('All Customer Groups')})
		group.insert()

	return group


def create_customer_address(customer, biotrack_customer):
	address1 = cstr(biotrack_customer.get("address1")).strip()

	if address1 == '':
		return

	address_type = _("Shop")
	if frappe.db.exists("Address", {"customer": customer.name, "address_line1": address1,
									"city": biotrack_customer.get("city"),
									"state": biotrack_customer.get("state")}):
		return

	idx = frappe.db.count("Address", {"customer": customer.name})

	address = frappe.get_doc(
		{
			"doctype": "Address",
			"address_title": customer.customer_name + (' - ' + str(idx) if idx > 0 else ''),
			"address_type": address_type,
			"customer": customer.name,
			"customer_name": customer.customer_name,
			"address_line1": address1,
			"address_line2": biotrack_customer.get("address2"),
			"city": biotrack_customer.get("city"),
			"state": biotrack_customer.get("state"),
			"pincode": biotrack_customer.get("zip"),
			"country": biotrack_customer.get("country") or frappe.defaults.get_defaults().get('country'),
		}
	)

	address.save()


def get_biotrack_vendors():
	data = get_data('sync_vendor', {'active': 1})
	return data.get('vendor') if bool(data.get('success')) else []
