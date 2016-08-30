# -*- coding: utf-8 -*-
# Copyright (c) 2015, Webonyx and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

# test_records = frappe.get_test_records('Plant')

class TestPlant(unittest.TestCase):
	pass


def test_insert():
	frappe.conf["biotrack.developer_mode"] = 1

	doc = frappe.get_doc({
		"doctype": "Plant",
		"item_group": "Plant Tissue",
		"source": "6033336840000140",
		"strain": "RaspberryKush",
		"warehouse": "Room4Row11 - EV",
	})

	doc.insert()
	doc.delete()

	print doc.as_dict()