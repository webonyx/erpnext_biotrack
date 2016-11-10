from __future__ import unicode_literals
import frappe
from erpnext import get_default_company
from .client import get_data


@frappe.whitelist()
def sync():
	synced_list = []
	for biotrack_room in get_biotrack_plant_rooms():
		if sync_plant_room(biotrack_room):
			synced_list.append(biotrack_room)

	return len(synced_list)


def sync_plant_room(biotrack_data):
	name = frappe.db.sql("SELECT name FROM `tabPlant Room` WHERE plant_room_name=%(plant_room_name)s OR external_id=%(external_id)s",
		{
			"plant_room_name": biotrack_data.get("name"),
			"external_id": biotrack_data.get("roomid")
		}
	, as_dict=True)

	if name:
		doc = frappe.get_doc("Plant Room", name[0])
		if doc.get("external_transaction_id") == biotrack_data.get("transactionid"):
			return False

	else:
		doc = frappe.get_doc({"doctype": "Plant Room", "company": get_default_company()})

	doc.update({
		"plant_room_name": biotrack_data.get("name"),
		"external_id": biotrack_data.get("roomid"),
		"external_transaction_id": biotrack_data.get("transactionid"),
		"disabled": biotrack_data.get("deleted"),
	})

	doc.save(ignore_permissions=True)
	frappe.db.commit()

	return True

def get_biotrack_plant_rooms(active=1):
	data = get_data('sync_plant_room', {'active': active})
	return data.get('plant_room') if bool(data.get('success')) else []
