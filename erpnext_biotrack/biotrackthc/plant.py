from __future__ import unicode_literals

import json

import frappe, datetime
from erpnext_biotrack.erpnext_biotrack.doctype.strain import find_strain
from erpnext_biotrack.item_utils import get_item_values

from .client import get_data
from frappe.utils.data import now, cint, DATE_FORMAT, TIME_FORMAT, DATETIME_FORMAT, get_datetime_str


@frappe.whitelist()
def sync():
	frappe.flags.in_import = True
	sync_time = now()

	biotrack_plants = get_biotrack_plants()
	for biotrack_plant in biotrack_plants:
		sync_plant(biotrack_plant)

	disable_deleted_plants(sync_time)
	frappe.flags.in_import = False

	return len(biotrack_plants)


def sync_plant(data):
	barcode = data.get("id")
	name = frappe.db.sql_list("select name from tabPlant where name=%(barcode)s or bio_barcode=%(barcode)s", {"barcode": barcode})

	if name:
		name = name.pop()
		doc = frappe.get_doc("Plant", name)
		if doc.get("bio_transaction_id") == data.get("transactionid"):
			frappe.db.set_value("Plant", name, "bio_last_sync", now(), update_modified=False)
			return False
	else:
		sessiontime = datetime.datetime.fromtimestamp(cint(data.get("sessiontime")))
		doc = frappe.get_doc({
			"__islocal": 1,
			"doctype": "Plant",
			"bio_barcode": barcode,
			"posting_date": sessiontime.strftime(DATE_FORMAT),
			"posting_time": sessiontime.strftime(TIME_FORMAT)
		})


	plant_room = frappe.get_doc("Plant Room", {"external_id": data.get("room")})
	doc.update({
		"strain": find_strain(data.get("strain")),
		"plant_room": plant_room.get("name") if plant_room else "",
		"is_mother_plant": cint(data.get("mother")),
		"destroy_scheduled": cint(data.get("removescheduled")),
		"harvest_collect": cint(data.get("harvestcollect")),
		"cure_collect": cint(data.get("curecollect")),
		"bio_transaction_id": cint(data.get("transactionid")),
		"bio_last_sync": now(),
		"disabled": 0,
	})

	item_values = get_item_values(data.get("parentid"), ["name", "item_group"])
	if item_values:
		item, item_group = item_values
		doc.item = item
		doc.item_group = item_group

	if doc.get("destroy_scheduled") and data.get("removescheduletime"):
		doc.remove_time = datetime.datetime.fromtimestamp(cint(data.get("removescheduletime"))).strftime(DATETIME_FORMAT)

		if data.get("removereason"):
			doc.remove_reason = data.get("removereason")

	state = cint(data.get("state"))
	doc.state = "Drying" if state == 1 else ("Cured" if state == 2 else "Growing")

	doc.flags.ignore_stock_update = True
	doc.flags.ignore_validate_update_after_submit = True
	doc.flags.ignore_mandatory = True

	if doc.is_new():
		doc.submit()
	else:
		doc.save()

	frappe.db.commit()


def disable_deleted_plants(sync_time):
	return frappe.db.sql(
		"update tabPlant set `disabled` = 1, destroy_scheduled = 1 where bio_transaction_id IS NOT NULL and (`bio_last_sync` IS NULL or `bio_last_sync` < %s)",
		sync_time
	)


def get_normalized():
	normalized = {}
	for plant in get_biotrack_plants():
		normalized[plant.get("id")] = plant

	return normalized


def get_biotrack_plants(active=1):
	data = get_data('sync_plant', {'active': active})
	return data.get('plant') if bool(data.get('success')) else []
