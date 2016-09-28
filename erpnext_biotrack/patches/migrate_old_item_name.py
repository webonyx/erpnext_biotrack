from __future__ import unicode_literals
import frappe
from erpnext_biotrack.biotrackthc.inventory import get_biotrack_inventories


def execute():
    """Replace item_code with barcode"""

    for biotrack_inventory in get_biotrack_inventories():
        barcode = str(biotrack_inventory.get("id"))

        # inventory type
        item_group = frappe.get_doc("Item Group", {"external_id": biotrack_inventory.get("inventorytype"),
                                                   "parent_item_group": "WA State Classifications"})

        # product (Item) mapping
        if biotrack_inventory.get("productname"):
            old_item_code = biotrack_inventory.get("productname")
            item_name = old_item_code
        else:
            old_item_code = "{0} - {1}".format(biotrack_inventory.get("strain"), item_group.name)
            item_name = "{0} - {1}".format(barcode[-4:], old_item_code)

        old_item_code = str(old_item_code).strip()
        item_name = str(item_name).strip()

        ret = frappe.db.sql_list(
            "select `name` from `tabItem` where (`barcode` IS NULL or `barcode` = '' or `barcode` = %(barcode)s) and `name` = %(name)s",
            {"name": old_item_code, "barcode": barcode}
        )

        if ret:
            frappe.db.sql(
                "UPDATE `tabItem` SET `name` = %(barcode)s, item_code = %(barcode)s, item_name = %(item_name)s, barcode = %(barcode)s WHERE `name` = %(old_item_code)s",
                {
                    "old_item_code": old_item_code,
                    "barcode": barcode,
                    "item_name": item_name,
                }
            )

        # item = frappe.get_doc("Item", ret[0])
        # item.update({
        # 	"item_code": barcode,
        # 	"item_name": item_name,
        # 	"barcode": barcode,
        # })
        # item.save()

        frappe.db.commit()
