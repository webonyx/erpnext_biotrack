# -*- coding: utf-8 -*-
# Copyright (c) 2016, Webonyx and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import json, os
import frappe
from frappe.model.db_schema import DbTable

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
                                                                                                   , "status": status,
                                                                                                "time": frappe.utils.now()}))
        if status == "Error" and not exception:
            status = "Queued"

        log.message += message if message else frappe.get_traceback()
        log.title = title[0:140] if title else (log.title if log.title else "Sync log")
        log.method = method
        log.status = status
        log.request_data = json.dumps(request_data)

        log.save(ignore_permissions=True)
        frappe.db.commit()

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
