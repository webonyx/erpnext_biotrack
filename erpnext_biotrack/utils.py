# -*- coding: utf-8 -*-
# Copyright (c) 2016, Webonyx and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import json
import frappe
from frappe.model.db_schema import DbTable
from .exceptions import BiotrackSetupError
from .exceptions import BiotrackError
from frappe.defaults import get_defaults
from frappe.desk.tags import DocTags
from frappe.exceptions import DoesNotExistError


def get_biotrack_settings():
	d = frappe.get_doc("BioTrack Settings")
	d.password = d.get_password()

	if d.username and d.license_number:
		return d.as_dict()
	else:
		frappe.throw(_("BioTrack credentials are not configured on BioTrack Settings"), BiotrackError)


def disable_biotrack_sync_on_exception():
	frappe.db.rollback()
	frappe.db.set_value("BioTrack Settings", None, "enable_biotrack", 0)
	frappe.db.set_value("BioTrack Settings", None, "session_id", '')
	frappe.db.commit()


def is_biotrack_enabled():
	biotrack_settings = frappe.get_doc("BioTrack Settings")
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
		name = frappe.db.get_value("BioTrack Log", {"status": "Queued"})

		if name:
			""" if name not provided by log calling method then fetch existing queued state log"""
			log = frappe.get_doc("BioTrack Log", name)

		else:
			""" if queued job is not found create a new one."""
			log = frappe.get_doc({"doctype": "BioTrack Log"}).insert(ignore_permissions=True)

		if exception:
			frappe.db.rollback()
			log = frappe.get_doc({"doctype": "BioTrack Log"}).insert(ignore_permissions=True)

		log.message = message if message else frappe.get_traceback()
		log.title = title[0:140]
		log.method = method
		log.status = status
		log.request_data = json.dumps(request_data)

		log.save(ignore_permissions=True)
		frappe.db.commit()


def get_default_company():
	return frappe.get_value("BioTrack Settings", None, 'custom_company') or get_defaults().get("company")


def skip_on_duplicating():
	return frappe.get_value("BioTrack Settings", None, 'skip_on_duplicate') or False


def add_tag(doctype, name, tag):
	DocTags(doctype).add(name, tag)

	return tag


def create_or_update_warehouse(biotrack_room, is_plant_room=0, synced_list=[]):
	try:
		warehouse = frappe.get_doc('Warehouse', {
			'external_id': biotrack_room.get('roomid'),
			'plant_room': is_plant_room})

		if not warehouse.wa_state_compliance_sync:
			return

	except DoesNotExistError:
		warehouse = frappe.new_doc('Warehouse')
		warehouse.update({
			'doctype': 'Warehouse',
			'company': get_default_company(),
			'wa_state_compliance_sync': 1,
			'plant_room': is_plant_room,
			'external_id': biotrack_room.get('roomid'),
		})

	if is_plant_room:
		under_account = frappe.get_value("BioTrack Settings", None, 'plant_room_parent_account')
	else:
		under_account = frappe.get_value("BioTrack Settings", None, 'inventory_room_parent_account')

	warehouse.update({
		"warehouse_name": biotrack_room.get("name"),
		"create_account_under": under_account,
		"external_transaction_id": biotrack_room.get("transactionid"),
		"quarantine": biotrack_room.get("quarantine") or 0
	})

	fix_duplicate(warehouse)

	warehouse.save(ignore_permissions=True)
	frappe.db.commit()
	synced_list.append(warehouse.external_transaction_id)


def fix_duplicate(warehouse, is_plant_room=0):
	suffix = " - " + frappe.db.get_value("Company", warehouse.company, "abbr")
	name = warehouse.warehouse_name + suffix

	if not frappe.db.exists('Warehouse', name):
		return

	# todo use de_duplicate helper instead
	for index in range(1, 11):
		warehouse_name = '{0} {1}'.format(warehouse.warehouse_name, index)
		name = warehouse_name + suffix
		if not frappe.db.exists('Warehouse', name):
			warehouse.set('warehouse_name', warehouse_name)
			return

def rename_custom_field(doctype, old_fieldname, new_fieldname):
	if not frappe.db.exists('DocType', doctype):
		return

	tab = DbTable(doctype)
	frappe.db.commit()

	columns = tab.columns
	# if old_fieldname not in columns:
	# 	return

	query = "change `{}` `{}` {}".format(old_fieldname, new_fieldname, tab.columns[old_fieldname].get_definition())

	frappe.db.sql("ALTER TABLE `{}` {}".format(tab.name, query))

	update_custom_field_sql = "UPDATE `tabCustom Field` SET `fieldname` = '{fieldname}', `name` = '{name}' WHERE `dt` = '{doctype}' AND `fieldname` ='{old_fieldname}'". \
		format(fieldname=new_fieldname, name="{}-{}".format(doctype, new_fieldname), doctype=doctype,
			   old_fieldname=old_fieldname)
	frappe.db.sql(update_custom_field_sql)

