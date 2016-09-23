from __future__ import unicode_literals
import frappe
from .client import get_data
from frappe import _
from frappe.exceptions import DoesNotExistError


@frappe.whitelist()
def sync():
    if not frappe.db.exists("Supplier Type", _("Lab & Scientific")):
        doc = frappe.get_doc({
            "doctype": "Supplier Type",
            "supplier_type": _("Lab & Scientific")
        })
        doc.save()
        frappe.db.commit()

    biotrack_labs = get_biotrack_labs()
    for biotrack_lab in biotrack_labs:
        sync_qa_lab(biotrack_lab)

    return len(biotrack_labs)


def sync_qa_lab(biotrack_lab):
    license_no = biotrack_lab.get("location")
    supplier_name = str(biotrack_lab.get("name")).strip()

    name = frappe.get_value("Supplier", {"license_no": license_no})

    if not name:
        doc = frappe.get_doc({
            "doctype": "Supplier",
            "supplier_name": supplier_name,
            "supplier_type": _("Lab & Scientific"),
            "license_no": license_no,
        })

        try:
            doc.save()
        except frappe.exceptions.DuplicateEntryError as ex:
            doc.set("supplier_name", "{} - {}".format(supplier_name, license_no))
            doc.save()
    else:
        doc = frappe.get_doc("Supplier", name)

    map_address(doc, biotrack_lab)
    frappe.db.commit()


def map_address(supplier, data):
    address1 = str(data.get("address1")).strip()
    if address1 == '':
        return

    address_type = _("Billing")
    name = str(supplier.supplier_name).strip() + "-" + address_type

    try:
        address = frappe.get_doc('Address', name)
    except DoesNotExistError as e:
        address = frappe.get_doc(
            {
                "doctype": "Address",
                "address_title": supplier.supplier_name,
                "address_type": address_type,
            }
        )

    address.update({
        "supplier": supplier.name,
        "supplier_name": supplier.supplier_name,
        "address_line1": address1,
        "address_line2": data.get("address2"),
        "city": data.get("city"),
        "state": data.get("state"),
        "pincode": data.get("zip"),
    })

    address.save()
    return address


def get_biotrack_labs(active=1):
    data = get_data('sync_qa_lab', {'active': active})
    return data.get('qa_lab') if bool(data.get('success')) else []
