from __future__ import unicode_literals

import frappe
import frappe.model.sync

def execute():
	# new doctype "Plant Room" added, need to sync model first
	frappe.model.sync.sync_all(verbose=True)

	for name in frappe.get_all("Warehouse", {"warehouse_type": "Plant Room"}):
		warehouse = frappe.get_doc("Warehouse", name)
		doc = frappe.new_doc("Plant Room")
		doc.update({
			"plant_room_name": warehouse.get("warehouse_name"),
			"company": warehouse.get("company"),
		})

		doc.save()

		frappe.db.sql(
			"UPDATE tabPlant SET plant_room=%(plant_room)s WHERE warehouse=%(warehouse)s",
			{
				"plant_room": doc.get("name"),
				"warehouse": warehouse.get("name"),
			}
		)

	frappe.db.sql(
		"DELETE FROM tabWarehouse WHERE warehouse_type=%(warehouse_type)s",
		{
			"warehouse_type": "Plant Room",
		}
	)

	frappe.delete_doc_if_exists("Custom Field", "Warehouse-warehouse_type")
