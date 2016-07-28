# -*- coding: utf-8 -*-
# Copyright Webonyx and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from .utils import make_log

@frappe.whitelist()
def sync():
	"Enqueue longjob for syncing biotrack."

	from frappe.utils.background_jobs import enqueue
	enqueue(sync_all)

	frappe.msgprint("Queued for syncing. It may take a few minutes to an hour.")

def sync_all():
	sources = ['biotrack']
	make_log(title="Sync Job is started", status="Queued", method="sync_all", message="Started")
	for s in sources:
		sync_source(s)

	make_log(title="Sync Completed", status="Success", method="sync_all", message="Completed")

def sync_source(source):
	script = "erpnext_biotrack.sources.%s" % source
	frappe.get_attr(script + ".sync")()

def hourly():
	return sync_if('Hourly')


def daily():
	return sync_if('Daily')


def weekly():
	return sync_if('Weekly')


def sync_if(schedule, default='Daily'):
	schedule_config = frappe.get_value("BioTrack Settings", None, 'schedule_in') or default

	if schedule_config == schedule:
		sync_all()
