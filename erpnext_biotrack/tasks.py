# -*- coding: utf-8 -*-
# Copyright Webonyx and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils.background_jobs import enqueue


@frappe.whitelist()
def sync():
	"Enqueue longjob for syncing biotrack."
	settings = frappe.get_doc("BioTrack Settings")
	if not settings.is_sync_enabled():
		frappe.msgprint('BioTrackTHC Background Syncing is not enabled.', title='Sync Error', indicator='red')
		return

	enqueue(sync_all)

	frappe.msgprint("Queued for syncing. It may take a few minutes to an hour.")


@frappe.whitelist()
def client_sync(doctype):
	"Enqueue longjob for syncing biotrack."
	settings = frappe.get_doc("BioTrack Settings")
	if not settings.enable_biotrack:
		frappe.msgprint('BioTrackTHC is not enabled.', title='Error', indicator='red')
		return

	enqueue(async_client_sync, queue="long", doctype=doctype)
	frappe.msgprint("Synchronization is enqueued.")


def async_client_sync(doctype):
	if doctype == "Plant":
		from .biotrackthc.plant import sync
		sync()
	elif doctype == "Item":
		from .biotrackthc.inventory import sync
		sync()
	elif doctype == "Customer":
		from .biotrackthc.vendor import sync
		sync()
	elif doctype == "Employee":
		from .biotrackthc.employee import sync
		sync()
	elif doctype == "Quality Inspection":
		from .biotrackthc.qa_sample import sync
		sync()
	elif doctype == "Warehouse":
		from .biotrackthc.inventory_room import sync
		from .biotrackthc.plant_room import sync as room_sync
		sync()
		room_sync()

	frappe.publish_realtime("list_update", {"doctype": doctype})


def sync_all():
	from .biotrackthc import sync
	sync()


def hourly():
	return sync_if('Hourly')


def daily():
	return sync_if('Daily')


def weekly():
	return sync_if('Weekly')


def sync_if(frequency, default='Daily'):
	settings = frappe.get_doc("BioTrack Settings")
	if settings.is_sync_enabled() and (settings.schedule_in or default) == frequency:
		sync_all()
