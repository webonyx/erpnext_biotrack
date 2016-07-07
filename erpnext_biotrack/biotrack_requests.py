from __future__ import unicode_literals
from datetime import datetime
import frappe
from frappe import _
import json
from .exceptions import BiotrackError
from .utils import get_biotrack_settings, disable_biotrack_sync_on_exception
from frappe.utils import get_request_session
from . import __api_version__, __api_endpoint__

def do_request(action, data=None):
	if not data:
		data = frappe._dict()

	biotrack_settings = get_biotrack_settings()

	data['action'] = action
	data['API'] = __api_version__
	data['username'] = biotrack_settings.username
	data['password'] = biotrack_settings.password
	data['license_number'] = biotrack_settings.license_number

	data['nosession'] = 1

	s = get_request_session()
	r = s.post(__api_endpoint__, data=json.dumps(data), headers=get_header())
	r.raise_for_status()

	result = r.json()
    #  todo handle errors
    # {"errorcode": "62", "success": 0, "error": "The current session does not possess access to the sync_employeess privilege."}
	# {"errorcode": "60", "success": 0, "error": "Invalid session."}

	if not result.get('success'):
		frappe.throw(result.get('error'), BiotrackError)

	return result

def login():
	biotrack_settings = frappe.get_doc("Biotrack Settings")

	s = get_request_session()
	r = s.post(__api_endpoint__, data=json.dumps({
		'API': __api_version__,
		'action': 'login',
		'license_number': biotrack_settings.license_number,
		'password': biotrack_settings.get_password(),
		'username': biotrack_settings.username,
	}), headers=get_header())

	r.raise_for_status()
	rs = r.json()

	if not rs.get('success'):
		disable_biotrack_sync_on_exception()
		frappe.throw(_("Biotrack authentication failed"), BiotrackError)

	biotrack_settings.session_id = rs.get('sessionid')
	biotrack_settings.session_time = datetime.fromtimestamp(rs.get('time'))
	biotrack_settings.save()

	return biotrack_settings.session_id


def get_header():
	return {'Content-Type': 'application/json'}
