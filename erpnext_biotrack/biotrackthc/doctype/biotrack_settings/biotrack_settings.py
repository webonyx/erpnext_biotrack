# -*- coding: utf-8 -*-
# Copyright (c) 2015, Webonyx and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from erpnext_biotrack.biotrackthc.client import get_client, BioTrackClientError
from frappe.model.document import Document

class BioTrackSettings(Document):
	def validate(self):
		if self.enabled:
			self.validate_access()

	def validate_access(self):
		client = get_client(self.license_number, self.username, self.get_password(), self.is_training)
		try:
			client.login()
		except BioTrackClientError as ex:
			frappe.local.message_log = []
			frappe.msgprint(ex.message, indicator='red', title='Access Error')

	def is_sync_down_enabled(self):
		return True if self.enabled and (self.synchronization == "All" or self.synchronization == "Down") else False

	def is_sync_up_enabled(self):
		return True if self.enabled and (self.synchronization == "All" or self.synchronization == "Up") else False
