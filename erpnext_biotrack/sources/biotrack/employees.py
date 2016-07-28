from __future__ import unicode_literals
import frappe
from datetime import date
from frappe.exceptions import DoesNotExistError
from frappe.defaults import get_defaults
from erpnext_biotrack.utils import make_log
from client import get_data


def sync():
	biotrack_employee_list = []
	biotrack_settings = frappe.get_doc("BioTrack Settings")
	company = biotrack_settings.custom_company or get_defaults().get("company")

	for biotrack_employee in get_biotrack_employees():
		create_or_update_employee(biotrack_employee, company, biotrack_employee_list)

	return len(biotrack_employee_list)


def create_or_update_employee(biotrack_employee, company, biotrack_employee_list):
	try:
		employee = frappe.get_doc("Employee", {'external_id': biotrack_employee.get("employee_id")})
		if not employee.wa_state_compliance_sync:
			return
	except DoesNotExistError as e:
		employee = frappe.get_doc({'doctype':'Employee'})

	date_of_birth = date(int(biotrack_employee.get("birthyear")), int(biotrack_employee.get("birthmonth")), int(biotrack_employee.get("birthday")))
	date_of_joining = date(int(biotrack_employee.get("hireyear")), int(biotrack_employee.get("hiremonth")), int(biotrack_employee.get("hireday")))

	try:
		employee.update({
			"employee_name": biotrack_employee.get("employee_name"),
			"external_id": biotrack_employee.get("employee_id"),
			"external_transaction_id": biotrack_employee.get("transactionid"),
			"wa_state_compliance_sync": 1,
			"company": company,
			"date_of_birth": date_of_birth,
			"date_of_joining": date_of_joining,
		})

		employee.flags.ignore_mandatory = True
		employee.save()

		biotrack_employee_list.append(biotrack_employee.get("employee_id"))
		frappe.db.commit()

	except Exception as e:
		make_log(title=e.message, status="Error", method="create_employee", message=frappe.get_traceback(),
						  request_data=biotrack_employee, exception=True)


def get_biotrack_employees():
	data = get_data('sync_employee', {'active': 1})

	return data.get('employee') if bool(data.get('success')) else []
