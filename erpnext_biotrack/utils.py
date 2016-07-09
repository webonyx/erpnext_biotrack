# -*- coding: utf-8 -*-
# Copyright (c) 2016, Webonyx and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import json
import frappe
from .exceptions import BiotrackSetupError
from .exceptions import BiotrackError
from frappe.defaults import get_defaults
from frappe.desk.tags import DocTags
from frappe.exceptions import DoesNotExistError


def get_biotrack_settings():
	d = frappe.get_doc("Biotrack Settings")
	d.password = d.get_password()

	if d.username and d.license_number:
		return d.as_dict()
	else:
		frappe.throw(_("Biotrack credentials are not configured on Biotrack Settings"), BiotrackError)


def disable_biotrack_sync_on_exception():
	frappe.db.rollback()
	frappe.db.set_value("Biotrack Settings", None, "enable_biotrack", 0)
	frappe.db.set_value("Biotrack Settings", None, "session_id", '')
	frappe.db.commit()


def is_biotrack_enabled():
	biotrack_settings = frappe.get_doc("Biotrack Settings")
	if not biotrack_settings.enable_biotrack:
		return False
	try:
		biotrack_settings.validate()
	except BiotrackSetupError:
		return False

	return True


def make_biotrack_log(title="Sync Log", status="Queued", method="sync_biotrack", message=None, exception=False,
					  name=None, request_data={}):
	if not name:
		name = frappe.db.get_value("Biotrack Log", {"status": "Queued"})

		if name:
			""" if name not provided by log calling method then fetch existing queued state log"""
			log = frappe.get_doc("Biotrack Log", name)

		else:
			""" if queued job is not found create a new one."""
			log = frappe.get_doc({"doctype": "Biotrack Log"}).insert(ignore_permissions=True)

		if exception:
			frappe.db.rollback()
			log = frappe.get_doc({"doctype": "Biotrack Log"}).insert(ignore_permissions=True)

		log.message = message if message else frappe.get_traceback()
		log.title = title[0:140]
		log.method = method
		log.status = status
		log.request_data = json.dumps(request_data)

		log.save(ignore_permissions=True)
		frappe.db.commit()


def get_default_company():
	return frappe.get_value("Biotrack Settings", None, 'custom_company') or get_defaults().get("company")


def skip_on_duplicating():
	return frappe.get_value("Biotrack Settings", None, 'skip_on_duplicate') or False


def add_tag(doctype, name, tag):
	DocTags(doctype).add(name, tag)

	return tag


def create_or_update_warehouse(biotrack_room, is_plant_room=0, synced_list=[]):
	try:
		warehouse = frappe.get_doc('Warehouse', {
			'biotrack_room_id': biotrack_room.get('roomid'),
			'biotrack_warehouse_is_plant_room': is_plant_room})

		if not warehouse.biotrack_warehouse_sync:
			return

	except DoesNotExistError:
		warehouse = frappe.new_doc('Warehouse')
		warehouse.update({
			'doctype': 'Warehouse',
			'company': get_default_company(),
			'biotrack_warehouse_sync': 1,
			'biotrack_warehouse_is_plant_room': is_plant_room,
			'biotrack_room_id': biotrack_room.get('roomid'),
			'biotrack_warehouse_transaction_id_original': biotrack_room.get('transactionid_original')
		})

	if is_plant_room:
		under_account = frappe.get_value("Biotrack Settings", None, 'plant_room_parent_account')
	else:
		under_account = frappe.get_value("Biotrack Settings", None, 'inventory_room_parent_account')

	warehouse.update({
		"warehouse_name": biotrack_room.get("name"),
		"create_account_under": under_account,
		"biotrack_warehouse_location_id": biotrack_room.get("location"),
		"biotrack_warehouse_transaction_id": biotrack_room.get("transactionid"),
		"biotrack_warehouse_quarantine": biotrack_room.get("quarantine") or 0
	})

	fix_duplicate(warehouse)

	warehouse.save(ignore_permissions=True)
	frappe.db.commit()
	synced_list.append(warehouse.biotrack_room_id)


def fix_duplicate(warehouse, is_plant_room=0):
	suffix = " - " + frappe.db.get_value("Company", warehouse.company, "abbr")
	name = warehouse.warehouse_name + suffix

	if not frappe.db.exists('Warehouse', name):
		return

	for index in range(1, 11):
		warehouse_name = '{0} {1}'.format(warehouse.warehouse_name, index)
		name = warehouse_name + suffix
		if not frappe.db.exists('Warehouse', name):
			warehouse.set('warehouse_name', warehouse_name)
			return
