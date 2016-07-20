from __future__ import unicode_literals
from erpnext_biotrack.install.after_install import create_weight_uom


def execute():
	create_weight_uom()
