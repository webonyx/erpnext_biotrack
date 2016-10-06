from __future__ import unicode_literals
import frappe, datetime
from .client import get_data
from frappe import _
from frappe.exceptions import DoesNotExistError, ValidationError
from frappe.utils.data import get_datetime_str


@frappe.whitelist()
def sync():
	synced_manifests = []
	biotrack_manifests = get_biotrack_manifests()
	for manifest_id, data in list(biotrack_manifests.items()):
		if sync_manifest(data):
			synced_manifests.append(manifest_id)

	return len(synced_manifests)


def sync_manifest(data):
	barcode = data.get("manifestid")
	docs = []

	for stop in data.get("stops"):
		customer_name = frappe.get_value("Customer", {"license_no": stop.get("license_number")})
		if not customer_name:
			continue
		else:
			customer = frappe.get_doc("Customer", customer_name)
			if not frappe.db.exists("Delivery Note", {"external_id": barcode, "customer": customer.name}):
				posting_datetime = datetime.datetime.fromtimestamp(int(stop.get("sessiontime")))
				posting_date, posting_time = posting_datetime.strftime("%Y-%m-%d %H:%M:%S").split(" ")
				doc = frappe.get_doc(
					{
						"doctype": "Delivery Note",
						"external_id": barcode,
						"creation": get_datetime_str(posting_datetime),
						"posting_date": posting_date,
						"posting_time": posting_time,
						"arrive_datetime": get_datetime_str(
							datetime.datetime.fromtimestamp(int(stop.get("arrive_time")))),
						"depart_datetime": get_datetime_str(
							datetime.datetime.fromtimestamp(int(stop.get("depart_time")))),
						"customer": customer.name,
						"instructions": stop.get("travel_route"),
						"transporter_name": data.get("transporter_name"),
						"lr_no": data.get("transporter_vehicle_identification"),
					}
				)

				for item_data in stop.get("items"):
					if int(item_data.get("deleted")):
						continue

					item_barcode = item_data.get("inventoryid")
					item = frappe.db.exists("Item", item_barcode)
					if not item:
						# lookup again at sample
						inspection = frappe.db.exists("Quality Inspection", {"barcode": item_barcode})
						if not inspection:
							continue
						else:
							item_code = frappe.get_value("Quality Inspection", inspection, "item_code")
					else:
						item_code = frappe.get_value("Item", item, "item_code")

					dn_item = frappe.get_doc({
						"doctype": "Delivery Note Item",
						"item_code": item_code,
						"qty": item_data.get("quantity"),
						"parentfield": "items",
					})

					doc.get("items").append(dn_item)

				if len(doc.get("items")) > 0:
					address = map_address(customer, stop)
					if address:
						doc.set("shipping_address_name", address.name)

					try:
						doc.save()
						docs.append(doc)
					except ValidationError as e:
						pass

	doc_len = len(docs)
	if doc_len:
		frappe.db.commit()

	return doc_len


def map_address(customer, data):
	address1 = str(data.get("street")).strip()
	if address1 == '':
		return

	address_type = _("Shipping")
	name = str(customer.customer_name).strip() + "-" + address_type

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
		"city": data.get("city") or "City",
		"state": data.get("state"),
		"pincode": data.get("zip"),
		"is_shipping_address": 1,
	})

	address.save()
	return address


def get_biotrack_manifests(active=1):
	data = get_data('sync_manifest', {'active': active})
	manifests = {}

	for manifest in data.get("manifest"):
		stops = []
		for stop_data in data.get("manifest_stop_data"):
			if stop_data.get("manifestid") == manifest.get("manifestid"):
				items = []
				for item in data.get("manifest_stop_items"):
					if item.get("stopnumber") == stop_data.get("stopnumber") and stop_data.get(
							"manifestid") == item.get("manifestid"):
						items.append(item)
				stop_data["items"] = items
				stops.append(stop_data)

		manifest["stops"] = stops
		manifests[manifest.get("manifestid")] = manifest

	return manifests
