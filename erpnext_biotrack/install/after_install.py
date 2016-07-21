from __future__ import unicode_literals
import frappe
from frappe import _


def install_fixtures():
	records = [
		{
			'doctype': 'Item Group',
			'item_group_name': 'WA State Classifications',
			'is_group': 'Yes',
			'parent_item_group': _('All Item Groups'),
		},

		# UOM
		{'uom_name': _('Gram'), 'doctype': 'UOM', 'name': _('Gram')},
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


def create_weight_uom():
	pass
