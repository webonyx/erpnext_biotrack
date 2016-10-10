from __future__ import unicode_literals
import frappe


def execute():
	"""bench execute erpnext_biotrack.patches.cleanup_items.execute"""
	frappe.flags.in_patch = True
	modified = '2016-10-10 01:47:11.767432'

	frappe.db.sql(
		"UPDATE tabItem set disabled = 1, modified = %(modified)s where transaction_id IS NULL and disabled = 0 and item_group IN (select name from `tabItem Group` where parent_item_group = %(parent_item_group)s)",
		{
			"modified": modified,
			"parent_item_group": "WA State Classifications"
		},
	)

	frappe.flags.in_patch = False
