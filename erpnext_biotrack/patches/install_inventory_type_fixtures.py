from __future__ import unicode_literals

import frappe


def execute():
    if not frappe.db.exists("Item Group", {'item_group_name': 'WA State Classifications'}):
        from erpnext_biotrack.install.after_install import install_fixtures
        install_fixtures()
