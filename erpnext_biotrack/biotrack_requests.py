from __future__ import unicode_literals
from datetime import datetime
import frappe
from frappe import _
import json
from .exceptions import BiotrackError
from .utils import get_biotrack_settings, disable_biotrack_sync_on_exception
from .config import is_training_mode
from frappe.utils import get_request_session
from . import __api_version__, __api_endpoint__

def do_request(action, data=None):

	data = build_action_data(action, data)

	s = get_request_session()
	r = s.post(__api_endpoint__, data=json.dumps(data), headers=get_headers())
	r.raise_for_status()

	result = r.json()
    #  todo handle errors
    # {"errorcode": "62", "success": 0, "error": "The current session does not possess access to the sync_employeess privilege."}
	# {"errorcode": "60", "success": 0, "error": "Invalid session."}

	if not result.get('success'):
		frappe.throw(result.get('error'), BiotrackError)

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

def build_action_data(action, data = None):
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