# -*- coding: utf-8 -*-
# Copyright (c) 2015, Webonyx and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from erpnext_biotrack.biotrackthc.client import get_client, BioTrackClientError
from frappe.integration_broker.doctype.integration_service.integration_service import IntegrationService
from frappe.utils import call_hook_method
from frappe.utils.background_jobs import enqueue

class BioTrackSettings(IntegrationService):
	service_name = "BioTrack"
	scheduler_events = {
		"daily_long": [
			"erpnext_biotrack.biotrackthc.doctype.biotrack_settings.biotrack_settings.sync_daily"
		],
		"weekly_long": [
			"erpnext_biotrack.biotrackthc.doctype.biotrack_settings.biotrack_settings.sync_weekly"
		]
	}

	def install_fixtures(self):
		pass

	def validate(self):
		if not self.flags.ignore_mandatory:
			self.validate_biotrack_credentails()

	def on_update(self):
		pass

	def enable(self):
		""" enable service """
		if not self.flags.ignore_mandatory:
			self.validate_biotrack_credentails()

	def validate_biotrack_credentails(self):
		client = get_client(self.license_number, self.username, self.get_password(), self.is_training)
		try:
			client.login()
		except BioTrackClientError as ex:
			frappe.local.message_log = []
			frappe.msgprint(ex.message, indicator='red', title='Invalid access credentials')

	def is_enabled(self):
		if not frappe.db.exists("Integration Service", self.service_name):
			return False

		service = frappe.get_doc("Integration Service", self.service_name)

		return service.enabled

	def is_sync_down_enabled(self):
		return True if self.is_enabled() and (self.synchronization == "All" or self.synchronization == "Down") else False

	def is_sync_up_enabled(self):
		return True if self.is_enabled() and (self.synchronization == "All" or self.synchronization == "Up") else False

	def create_request(self, data):
		return super(BioTrackSettings, self).create_request(data, "Host", self.service_name)


@frappe.whitelist()
def get_service_details():
	return """
	<div>
		<p>Steps to enable BioTrack service:</p>
		<ol>
			<li> Request api credentials at
				<a href="https://www.biotrack.com" target="_blank">
					https://www.biotrack.com
				</a>
			</li>
			<br>
			<li> Setup credentials on BioTrack Settings doctype.
				Click on
				<button class="btn btn-default btn-xs disabled"> BioTrack Settings </button>
				top right corner
			</li>
			<br>
			<li>
				After saving settings,
					<label>
						<span class="input-area">
							<input type="checkbox" class="input-with-feedback" checked disabled>
						</span>
						<span class="label-area small">Enable</span>
					</label>
				BioTrack Integration Service and Save a document.
			</li>
			<br>
			<li>
				To view api call logs,
				<button class="btn btn-default btn-xs disabled"> Show Log </button>
			</li>
		</ol>
		<p>
			After enabling service, system will synchrony data from BioTrack daily or weekly basis
			as per set on BioTrack Settings page. For detail what's data synced, see
			<a href="https://github.com/webonyx/erpnext_biotrack#doctype-mapping" target="_blank">
				Doctype Mappings
			</a> document.
		</p>
	</div>
	"""

@frappe.whitelist()
def sync_now(doctype=None):
	"Enqueue longjob for syncing biotrack."
	settings = frappe.get_doc("BioTrack Settings")
	if not settings.is_sync_down_enabled():
		frappe.msgprint('BioTrack service is not enabled.', title='Error', indicator='red')
		return

	from erpnext_biotrack.biotrackthc import sync

	force_sync = False
	if doctype:
		force_sync = True

	enqueue(sync, queue="long", doctype=doctype, force_sync=force_sync, async_notify=True)


def sync_daily():
	return sync_if('Daily')


def sync_weekly():
	return sync_if('Weekly')


def sync_if(frequency, default='Daily'):
	settings = frappe.get_doc("BioTrack Settings")
	if settings.is_sync_down_enabled() and (settings.sync_frequency or default) == frequency:
		from erpnext_biotrack.biotrackthc import sync
		sync()
		call_hook_method('biotrack_synced')