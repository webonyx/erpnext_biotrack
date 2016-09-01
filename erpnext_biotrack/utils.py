# -*- coding: utf-8 -*-
# Copyright (c) 2016, Webonyx and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import json, os
import frappe
from frappe.model.db_schema import DbTable
from frappe.utils.csvutils import read_csv_content
from .exceptions import BiotrackSetupError
from .exceptions import BiotrackError
from frappe.defaults import get_defaults
from frappe.desk.tags import DocTags
from frappe.exceptions import DoesNotExistError, ValidationError

dumped_data = {}
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


def make_log(title=None, status="Queued", method="sync", message=None, exception=False,
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


		log.message = (log.message + "\n\n" if log.message else "") + "{}\n".format(json.dumps({"method": method
																								, "status": status, "time": frappe.utils.now()}))
		if status == "Error" and not exception:
			status = "Queued"

		log.message += message if message else frappe.get_traceback()
		log.title = title[0:140] if title else (log.title if log.title else "Sync log")
		log.method = method
		log.status = status
		log.request_data = json.dumps(request_data)

		log.save(ignore_permissions=True)
		frappe.db.commit()


def get_default_company():
	return frappe.get_value("BioTrack Settings", None, 'custom_company') or get_defaults().get("company")


def add_tag(doctype, name, tag):
	DocTags(doctype).add(name, tag)

	return tag


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


def inventories_price_log():
	if not "inventories_price" in dumped_data:
		inventories_price = {}
		for row in load_dumped_data("inventorytransfers_log"):
			inventory_id = row[2]
			price = row[19]

			if inventory_id not in inventories_price:
				inventories_price[inventory_id] = []

			inventories_price[inventory_id].append(price)
		dumped_data["inventories_price"] = inventories_price

	return dumped_data["inventories_price"]


def load_dumped_data(name):
	if not name in dumped_data:
		filename = name + '.csv'
		file = frappe.get_app_path("erpnext_biotrack", "fixtures/dump", filename)
		if os.path.exists(file):
			with open(file, "r") as csvfile:
				fcontent = csvfile.read()
				dumped_data[name] = read_csv_content(fcontent, False)
		else:
			raise ValidationError, "Dumped file {} does not exists".format(filename)

	return dumped_data[name]