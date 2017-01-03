# -*- coding: utf-8 -*-
# Copyright (c) 2015, Webonyx and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

test_records = frappe.get_test_records('Strain')

class TestStrain(unittest.TestCase):
	pass
