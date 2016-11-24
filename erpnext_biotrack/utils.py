# -*- coding: utf-8 -*-
# Copyright (c) 2016, Webonyx and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.db_schema import DbTable


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
