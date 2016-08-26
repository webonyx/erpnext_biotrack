import frappe
from .client import BioTrackClientError

def _validate_data(attrs, data):
	for key in attrs:
		if key not in data:
			raise BioTrackClientError('"{} is required"'.format(key))

	return True

def random_digits(length):
	"""generate a random string"""
	import string
	from random import choice
	return ''.join([choice(string.digits) for i in range(length)])

def post(action, data=None):
	action = frappe.get_attr(__name__ + "." + action)
	return action(data)

def inventory_new(data):
	_validate_data([
		"data",
		"location",
	], data)

	_validate_data([
		"invtype",
		"quantity",
		"strain",
	], data.get("data"))

	return frappe._dict({
		"barcode_id": [random_digits(16)],
		"sessiontime": 1,
		"success": 1,
		"transactionid": random_digits(4),
	})