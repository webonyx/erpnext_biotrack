import sys
import frappe
from erpnext_biotrack.biotrackthc import sync_up_enabled, get_location, call
from erpnext_biotrack.biotrackthc.client import BioTrackClientError
from frappe.utils.data import cstr, cint, flt


def call_hook(plant, method, *args, **kwargs):
	if not sync_up_enabled():
		return

	return getattr(sys.modules[__name__], method)(plant, method, *args, **kwargs)


def is_bio_item(item):
	return cstr(item.get("bio_barcode")) != ""


def on_submit(doc, method):
	"""BioTrack sync up: inventory_new or inventory_adjust"""
	if doc.purpose == "Material Issue" and not doc.conversion:
		for item_entry in doc.get("items"):
			item = frappe.get_doc("Item", item_entry.item_code)
			if is_bio_item(item):
				if not item_entry.t_warehouse:
					_inventory_adjust(item, remove_quantity=item_entry.qty)
				# else:
					# inventory split and inventory_move

	elif doc.purpose == "Material Receipt":
		for item_entry in doc.get("items"):
			item = frappe.get_doc("Item", item_entry.item_code)

			if is_bio_item(item):
				_inventory_adjust(item, additional_quantity=item_entry.qty)

			# only sync up marijuana item
			elif item.is_marijuana_item:
				_inventory_new(item, item_entry.qty)

def _inventory_new(item, qty):
	item_group = frappe.get_doc("Item Group", item.item_group)
	if not item_group.external_id:
		frappe.throw("Invalid inventory type")

	if not item.strain:
		frappe.throw("strain is missing for item {0}".format(item.item_code))

	call_data = {
		"invtype": item_group.external_id,
		"quantity": qty,
		"strain": item.strain,
	}

	if item.plant:
		call_data["source_id"] = item.plant

	res = call("inventory_new", data={
		"data": call_data,
		"location": get_location()
	})

	item.update({
		"bio_barcode": res.get("barcode_id")[0],
		"bio_remaining_quantity": qty
	})

	item.save()

def _inventory_adjust(item, additional_quantity=None, remove_quantity=None):
	data = {
		"barcodeid": item.bio_barcode,
		"reason": "Client Adjustment",
		"type": 1,
		"remove_quantity_uom": "g",
	}

	if additional_quantity:
		item.bio_remaining_quantity = item.bio_remaining_quantity + additional_quantity

	elif remove_quantity:
		item.bio_remaining_quantity = item.bio_remaining_quantity - remove_quantity

	data["quantity"] = item.bio_remaining_quantity
	call("inventory_adjust", data={
		"data": data,
	})

	item.save()

def after_conversion(doc, method):
	qty = 0
	data = []

	for entry in doc.get("items"):
		bio_barcode = frappe.get_value("Item", entry.item_code, "bio_barcode")
		if not bio_barcode:
			frappe.throw(_("{0} is not a BioTrack Item. Consider to select BioTrack items only or turn off BioTrack synchronization").format(entry.item_code))

		data.append({
			"barcodeid": bio_barcode,
			"remove_quantity": entry.qty,
			"remove_quantity_uom": "g",
		})
		qty += entry.qty

	if doc.conversion == 'Create Lot':
		_create_lot(doc, data)
	else:
		_create_product(doc, data)

def _create_lot(stock_entry, data):
	try:
		res = call("inventory_create_lot", {"data": data})
		frappe.set_value("Item", stock_entry.lot_item, "bio_barcode", res.get("barcode_id"))
	except BioTrackClientError as ex:
		frappe.local.message_log.pop()
		frappe.throw(ex.message, title="BioTrack synchrony failed")

def _create_product(stock_entry, data):
	product_type = frappe.get_value("Item Group", stock_entry.product_group, "external_id")
	request_data = {}

	if not product_type:
		frappe.throw("Inventory type not found")

	request_data["data"] = data
	request_data["derivative_type"] = cint(product_type)
	request_data["derivative_quantity"] = flt(stock_entry.product_qty)
	request_data["derivative_quantity_uom"] = "g"
	request_data["waste"] = flt(stock_entry.product_waste)
	request_data["waste_uom"] = "g"

	product_usable = flt(stock_entry.product_usable)

	if product_usable > 0:
		request_data["derivative_usable"] = product_usable

	if stock_entry.product_name:
		request_data["derivative_product"] = stock_entry.product_name

	response = {}
	try:
		response = call("inventory_convert", request_data)
	except BioTrackClientError as ex:
		frappe.local.message_log.pop()
		frappe.throw(ex.message, title="BioTrack synchrony failed")

	derivatives = response.get("derivatives", [])

	for derivative in derivatives:
		item_type = derivative.get("barcode_type")
		barcode = derivative.get("barcode_id")

		if item_type == 27 and stock_entry.waste_item:
			frappe.set_value("Item", stock_entry.waste_item, "bio_barcode", barcode)

		elif item_type == product_type and stock_entry.product_item:
			frappe.set_value("Item", stock_entry.product_item, "bio_barcode", barcode)
