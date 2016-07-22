from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.exceptions import DoesNotExistError
from frappe.utils import cstr
from biotrack_requests import do_request
from frappe.utils.nestedset import get_root_of

def sync():
	synced_list = []
	for biotrack_customer in get_biotrack_vendors():
		create_or_update_customer(biotrack_customer, synced_list)

	return len(synced_list)

def create_or_update_customer(biotrack_customer, synced_list):
	# biotrack_settings = frappe.get_doc("BioTrack Settings", "BioTrack Settings")

	try:
		customer = frappe.get_doc('Customer', {'customer_name': biotrack_customer.get("name")})
		if not int(customer.biotrack_customer_sync):
			return
	except DoesNotExistError:
		customer = frappe.get_doc({
			"doctype": "Customer",
			"customer_name": biotrack_customer.get("name"),
			"territory": get_root_of("Territory"),
			"customer_type": _("Company"),
			"wa_state_compliance_sync": 1,
			"biotrack_customer_transaction_id_original": biotrack_customer.get("transactionid_original"),
		})

	customer_group = detect_group(biotrack_customer)
	customer.update({
		"customer_group": customer_group.name if customer_group else None,
		"territory": get_root_of("Territory"),
		"biotrack_customer_ubi": biotrack_customer.get("ubi"),
		"biotrack_customer_license": biotrack_customer.get("location"),
		"biotrack_customer_license_type": biotrack_customer.get("locationtype"),
		"biotrack_customer_transaction_id": biotrack_customer.get("transactionid")
	})

	customer.flags.ignore_mandatory = True
	customer.save()

	if customer:
		create_customer_address(customer, biotrack_customer)


	frappe.db.commit()
	synced_list.append(customer.biotrack_customer_ubi)


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
		group = frappe.get_doc({'doctype': 'Customer Group', 'name': name, 'customer_group_name': name, 'is_group': 'No', 'parent_customer_group': _('All Customer Groups')})
		group.insert()

	return group

def create_customer_address(customer, biotrack_customer):
	address1 = cstr(biotrack_customer.get("address1")).strip()

	if address1 == '':
		return

	address_type = _("Billing")
	name = cstr(customer.customer_name).strip() + "-" + address_type

	try:
		address = frappe.get_doc('Address', name)
	except DoesNotExistError as e:
		address = frappe.get_doc(
			{
				"doctype": "Address",
				"address_title": customer.customer_name,
				"address_type": address_type,
				"customer": customer.name,
				"customer_name": customer.customer_name
			}
		)

	address.update({
		"address_line1": address1,
		"address_line2": biotrack_customer.get("address2"),
		"city": biotrack_customer.get("city") or "City",
		"state": biotrack_customer.get("state"),
		"pincode": biotrack_customer.get("zip"),
		"country": biotrack_customer.get("country") or frappe.defaults.get_defaults().get('country'),
	})

	address.save()


def get_biotrack_vendors():
	data = do_request('sync_vendor', {'active': 1})
	return data.get('vendor') if bool(data.get('success')) else []

