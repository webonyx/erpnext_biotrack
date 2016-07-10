# -*- coding: utf-8 -*-
# Copyright (c) 2015, Webonyx and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class StockType(Document):
	def autoname(self):
		"""set name as type_name"""
		if not self.name:
			self.name = self.type_name
