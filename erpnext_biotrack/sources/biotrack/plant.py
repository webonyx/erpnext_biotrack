from __future__ import unicode_literals
import frappe, datetime
from client import get_data
from frappe.utils.data import get_datetime_str

@frappe.whitelist()
def sync():
    frappe.flags.in_import = True
    biotrack_plants = get_biotrack_plants()
    for biotrack_plant in biotrack_plants:
        sync_plant(biotrack_plant)

    frappe.flags.in_import = False
    return len(biotrack_plants)


def sync_plant(biotrack_plant):
    barcode = biotrack_plant.get("id")
    if frappe.db.exists("Plant", barcode):
        doc = frappe.get_doc("Plant", barcode)
    else:
        creation_datetime = datetime.datetime.fromtimestamp(int(biotrack_plant.get("sessiontime")))
        doc = frappe.get_doc({"doctype": "Plant", "barcode": barcode, "creation": get_datetime_str(creation_datetime)})

    doc.biotrack_sync_down(biotrack_plant)
    frappe.db.commit()

def get_biotrack_plants(active=1):
    data = get_data('sync_plant', {'active': active})
    return data.get('plant') if bool(data.get('success')) else []
