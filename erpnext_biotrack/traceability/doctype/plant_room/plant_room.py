# -*- coding: utf-8 -*-
# Copyright (c) 2015, Webonyx and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class PlantRoom(Document):
	def autoname(self):
		if self.company:
			suffix = " - " + frappe.db.get_value("Company", self.company, "abbr")
			if not self.plant_room_name.endswith(suffix):
				self.name = self.plant_room_name + suffix
		else:
			self.name = self.plant_room_name
