from __future__ import unicode_literals
from .client import post
import frappe

def call(fn, *args, **kwargs):
	if frappe.conf.get("biotrack.developer_mode"):
		from .client_dev import post as post_dev
		return post_dev(fn, *args, **kwargs)

	return post(fn, *args, **kwargs)