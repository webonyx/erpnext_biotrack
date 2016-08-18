from __future__ import unicode_literals
from datetime import datetime
import frappe, os
from frappe import _
import json
from erpnext_biotrack.exceptions import BiotrackError, BioTrackClientError
from erpnext_biotrack.utils import get_biotrack_settings, disable_biotrack_sync_on_exception
from erpnext_biotrack.config import is_training_mode
from frappe.utils import get_request_session, encode
from erpnext_biotrack import __api_version__, __api_endpoint__


def get_data(action, params=None, key=None):
	offline_sync = frappe.conf.get('erpnext_biotrack.offline_sync') or 0

	if offline_sync:
		from frappe.modules.import_file import read_doc_from_file
		filename = action + '.json'
		f = frappe.get_app_path("erpnext_biotrack", "fixtures/offline_sync", filename)
		if os.path.exists(f):
			data = read_doc_from_file(f)
		else:
			data = do_request(action=action, data=params, return_key=key)
			if not key and not data.get('success'):
				return data

			with open(f, "w") as outfile:
				outfile.write(frappe.as_json(data))

		return data
	else:
		return do_request(action=action, data=params, return_key=key)

def do_request(action, data=None, return_key=None):
	data = build_action_data(action, data)

	s = get_request_session()
	r = s.post(__api_endpoint__, data=json.dumps(data), headers=get_headers())
	r.raise_for_status()

	result = r.json()
	#  todo handle errors
	# {"errorcode": "62", "success": 0, "error": "The current session does not possess access to the sync_employeess privilege."}
	# {"errorcode": "60", "success": 0, "error": "Invalid session."}

	if not result.get('success'):
		raise BioTrackClientError(encode(result.get('error')))

	if return_key and return_key in result:
		return result[return_key]

	return result


def login():
	s = get_request_session()
	data = build_action_data('login')
	r = s.post(__api_endpoint__, data=json.dumps(data), headers=get_headers())

	r.raise_for_status()
	rs = r.json()

	if not rs.get('success'):
		disable_biotrack_sync_on_exception()
		frappe.throw(_("BioTrack authentication failed. {0}".format(rs.get('error'))), BiotrackError)

	biotrack_settings = frappe.get_doc("BioTrack Settings")
	biotrack_settings.session_id = rs.get('sessionid')
	biotrack_settings.session_time = datetime.fromtimestamp(rs.get('time'))
	biotrack_settings.save()

	return biotrack_settings


def get_headers():
	return {'Content-Type': 'application/json'}


def build_action_data(action, data=None):
	if not data:
		data = frappe._dict()

	biotrack_settings = get_biotrack_settings()

	data['action'] = action
	data['API'] = __api_version__
	data['username'] = biotrack_settings.username
	data['password'] = biotrack_settings.password
	data['license_number'] = biotrack_settings.license_number

	if action != 'login':
		data['nosession'] = 1

	if is_training_mode():
		data['training'] = 1

	return data
