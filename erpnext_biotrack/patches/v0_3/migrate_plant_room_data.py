from __future__ import unicode_literals

import frappe
import frappe.model.sync
from frappe.utils.fixtures import sync_fixtures


def execute():
	app = __name__.split(".")[0]
	sync_fixtures(app)

	frappe.db.sql("UPDATE `tabPlant Room` SET bio_id=ifnull(external_id, 0), bio_transactionid=external_transaction_id WHERE bio_id=0")

