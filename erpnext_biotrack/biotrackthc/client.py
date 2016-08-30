import json, frappe
from frappe.utils import get_request_session, encode

class BioTrackClientError(frappe.ValidationError):
	http_status_code = 500

	def __init__(self, *args, **kwargs):
		if len(args) and isinstance(args[0], basestring):
			frappe.local.message_log.append(args[0])

		super(frappe.ValidationError, self).__init__(*args, **kwargs)

class BioTrackEmptyDataError(BioTrackClientError): pass

class BioTrackClient:
	__API__ = "4.0"
	__API_URL__ = "https://wslcb.mjtraceability.com/serverjson.asp"

	def __init__(self, license_number, username, password, is_training=0):
		self.license_number = license_number
		self.username = username
		self.password = password
		self.is_training = is_training

	def post(self, action, data, raise_on_empty=True):
		if not isinstance(data, dict):
			raise BioTrackClientError("data must be instance of dict")

		data["action"] = action
		action_data = data.copy()

		data.update({
			"license_number": self.license_number,
			"username": self.username,
			"password": self.password,
			"training": self.is_training,
			"API": self.__API__,
		})

		if action != 'login':
			data["nosession"] = 1

		if (frappe.conf.get("logging") or 0) > 0:
			frappe.log("<<<< BioTrackTHC")
			frappe.log(json.dumps(action_data))
			frappe.log(">>>>")

		request = get_request_session()
		response = request.post(self.__API_URL__, data=json.dumps(data), headers={'Content-Type': 'application/json'})
		response.raise_for_status()
		result = response.json()

		if not result.get('success'):
			raise BioTrackClientError(encode(result.get('error')))

		if raise_on_empty and len(result) == 1:
			raise BioTrackEmptyDataError(
				'BioTrackTHC request was response empty data: {}'.format(json.dumps(action_data))
			)

		return result

	def login(self):
		return self.post('login', {})

def get_client(license_number, username, password, is_training=0):
	"""
	:return BioTrackClient:
	"""
	return BioTrackClient(license_number, username, password, is_training)

def post(action, data):
	settings = frappe.get_doc("BioTrack Settings")
	if not settings.enable_biotrack:
		raise BioTrackClientError('BioTrackTHC integration is not enabled')

	client = get_client(settings.license_number, settings.username, settings.get_password(), settings.is_training)
	return client.post(action, data)