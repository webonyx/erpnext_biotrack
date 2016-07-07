from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.exceptions import DoesNotExistError
from .utils import skip_on_duplicating, add_tag, make_biotrack_log
from biotrack_requests import do_request
from frappe.utils import cint
from frappe.utils.nestedset import get_root_of

def sync():
	synced_list = []
	for biotrack_customer in get_biotrack_vendors():
		if skip_on_duplicating():
			if frappe.db.exists({'doctype': 'Customer', 'customer_name': biotrack_customer.get("name")}):
				continue

			create_customer(biotrack_customer, synced_list)

	return len(synced_list)

def create_customer(biotrack_customer, synced_list):
	biotrack_settings = frappe.get_doc("Biotrack Settings", "Biotrack Settings")

	try:
		customer = frappe.get_doc('Customer', {'customer_name': biotrack_customer.get("name")})
		if not cint(customer.biotrack_customer_sync):
			return
	except DoesNotExistError as e:

		customer = frappe.get_doc({
			"doctype": "Customer",
			"customer_name": biotrack_customer.get("name"),
			"customer_group": biotrack_settings.customer_group,
			"territory": get_root_of("Territory"),
			"customer_type": _("Company"),
			"biotrack_customer_sync": 1,
			"biotrack_customer_ubi": biotrack_customer.get("ubi"),
			"biotrack_customer_location": biotrack_customer.get("location"),
			"biotrack_customer_location_type": biotrack_customer.get("locationtype"),
			"biotrack_customer_transaction_id": biotrack_customer.get("transactionid"),
			"biotrack_customer_transaction_id_original": biotrack_customer.get("transactionid_original"),
		})

	customer.flags.ignore_mandatory = True
	customer.save()

	if customer:
		create_customer_address(customer, biotrack_customer)

	if cint(biotrack_customer.get("producer")):
		add_tag("Customer", customer.name, "producer")
	elif cint(biotrack_customer.get("retail")):
		add_tag("Customer", customer.name, "retail")
	elif cint(biotrack_customer.get("processor")):
		add_tag("Customer", customer.name, "processor")

	frappe.db.commit()
	synced_list.append(customer.biotrack_customer_ubi)


def create_customer_address(customer, biotrack_customer):
	if frappe.db.exists({'doctype': 'Address', 'customer_name': customer.customer_name, 'address_title': customer.customer_name}):
		return

	if biotrack_customer.get("address1"):
		try:
			frappe.get_doc({
				"doctype": "Address",
				"address_title": customer.customer_name,
				"address_type": _("Billing"),
				"address_line1": biotrack_customer.get("address1") or "Address 1",
				"address_line2": biotrack_customer.get("address2"),
				"city": biotrack_customer.get("city") or "City",
				"state": biotrack_customer.get("state"),
				"pincode": biotrack_customer.get("zip"),
				"country": biotrack_customer.get("country") or frappe.defaults.get_defaults().get('country'),
				"customer": customer.name,
				"customer_name": customer.customer_name
			}).insert()

		except Exception as e:
			make_biotrack_log(title=e.message, status="Error", method="create_customer_address",
							  message=frappe.get_traceback(),
							  request_data=biotrack_customer, exception=True)


def get_biotrack_vendors():
	data = do_request('sync_vendor')
	return data.get('vendor') if bool(data.get('success')) else []

