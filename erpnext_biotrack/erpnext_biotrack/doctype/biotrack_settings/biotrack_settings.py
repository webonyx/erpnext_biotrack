# -*- coding: utf-8 -*-
# Copyright (c) 2015, Webonyx and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from erpnext_biotrack.biotrackthc.client import get_client, BioTrackClientError
from frappe.model.document import Document
from frappe.utils.data import cint

class BioTrackSettings(Document):
	def validate(self):
		if self.enable_biotrack == 1:
			self.validate_access()

	def validate_access(self):
		client = get_client(self.license_number, self.username, self.get_password(), self.is_training)
		try:
			client.login()
		except BioTrackClientError as ex:
			frappe.local.message_log = []
			frappe.msgprint(ex.message, indicator='red', title='Access Error')

	def get_password(self, fieldname='password', raise_exception=True):
		""" This fix because master branch is still storing raw password in database """
		try:
			return super(Document, self).get_password(fieldname, raise_exception)
		except AttributeError:
			return self.get(fieldname)


	def is_enabled(self):
		return cint(self.enable_biotrack)


	def is_sync_enabled(self):
		return cint(self.enable_biotrack) and cint(self.sync_enabled)