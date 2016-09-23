from __future__ import unicode_literals

import frappe
from erpnext_biotrack.biotrackthc.vendor import get_biotrack_vendors


def execute():
    frappe.flags.in_import = True
    frappe.get_doc({
        "doctype": "Custom Field",
        "dt": "Customer",
        "fieldname": "duplicate",
        "fieldtype": "Check",
    }).insert()

    frappe.db.commit()

    for biotrack_customer in get_biotrack_vendors():
        if frappe.db.exists("Customer", biotrack_customer.get("name")):
            frappe.db.sql(
                "UPDATE `tabCustomer` SET `duplicate`=1 WHERE `name` != %(name)s AND customer_name = %(name)s",
                {"name": biotrack_customer.get("name")})

    frappe.db.commit()

    for name in frappe.get_list("Customer", {"duplicate": 1}):
        frappe.get_doc("Customer", name).delete()
        print "Deleted " + name['name']

    frappe.db.commit()

    frappe.get_doc("Custom Field", "Customer-duplicate").delete()
