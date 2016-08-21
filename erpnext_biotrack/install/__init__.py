from __future__ import unicode_literals
import frappe
from erpnext import get_default_company
from frappe import _
from frappe.utils.fixtures import sync_fixtures


def after_install():
	app = __name__.split(".")[0]
	sync_fixtures(app)
	install_fixtures()

def install_fixtures():
	records = [
		{
			'doctype': 'Item Group',
			'item_group_name': 'WA State Classifications',
			'is_group': 1,
			'parent_item_group': _('All Item Groups'),
		},
	]

	for r in records:
		doc = frappe.new_doc(r.get("doctype"))
		doc.update(r)

		try:
			doc.insert(ignore_permissions=True)
		except frappe.DuplicateEntryError, e:
			# pass DuplicateEntryError and continue
			if e.args and e.args[0] == doc.doctype and e.args[1] == doc.name:
				# make sure DuplicateEntryError is for the exact same doc and not a related doc
				pass
			else:
				raise
	frappe.db.commit()

	from .inventory_types import item_groups_data
	for data in item_groups_data:
		if not frappe.db.exists("Item Group", data):
			doc = frappe.new_doc("Item Group")

			data["parent_item_group"] = "WA State Classifications"
			data["is_group"] = 0

			doc.update(data)
			doc.insert()

	frappe.db.commit()


	company = get_default_company()
	if not frappe.db.exists("Account", {"account_name": "Plant Room Assets", "company": company}):
		parent_account = frappe.get_value("Account", {"company": company, "account_name": "Current Assets"})
		doc = frappe.get_doc({
			"doctype": "Account",
			"account_name": "Plant Room Assets",
			"company": company,
			"is_group": 1,
			"root_type": "Asset",
			"parent_account": parent_account,
		})
		doc.insert(ignore_permissions=True)

	bio_settings = frappe.get_doc("BioTrack Settings")
	bio_settings.plant_room_parent_account = frappe.get_value("Account", {"company": company, "account_name": "Plant Room Assets"})
	bio_settings.inventory_room_parent_account = frappe.get_value("Account", {"company": company, "account_name": "Stock Assets"})

	bio_settings.flags.ignore_mandatory = True
	bio_settings.save()