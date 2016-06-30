# -*- coding: utf-8 -*-
# Copyright (c) 2015, Webonyx and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from erpnext_biotrack.exceptions import BiotrackSetupError

class BiotrackSettings(Document):
	def validate(self):
		if self.enable_biotrack == 1:
			self.validate_access_credentials()
			self.validate_access()

	def validate_access_credentials(self):
		if not (self.username and  self.password and self.license_number):
			frappe.msgprint(_("Missing value for License number, username and password"),
							raise_exception=BiotrackSetupError)

	def validate_access(self): pass