from __future__ import unicode_literals
import frappe
from datetime import date

from .utils import make_biotrack_log
from erpnext import get_default_company

from biotrack_requests import do_request

def sync_employees():
	biotrack_employee_list = []

	for biotrack_employee in get_biotrack_employees():
		if not frappe.db.get_value("Employee", {"biotrack_employee_id": biotrack_employee.get('employee_id')}, "name"):
			create_employee(biotrack_employee, biotrack_employee_list)

	return len(biotrack_employee_list)

def create_employee(biotrack_employee, biotrack_employee_list):
	biotrack_settings = frappe.get_doc("Biotrack Settings", "Biotrack Settings")
	date_of_birth = date(int(biotrack_employee.get("birthyear")), int(biotrack_employee.get("birthmonth")), int(biotrack_employee.get("birthday")))
	date_of_joining = date(int(biotrack_employee.get("hireyear")), int(biotrack_employee.get("hiremonth")), int(biotrack_employee.get("hireday")))

	try:
		employee = frappe.get_doc({
			"doctype": "Employee",
			"name": biotrack_employee.get("employee_id"),
			"employee_name": biotrack_employee.get("employee_name"),
			"biotrack_employee_id": biotrack_employee.get("employee_id"),
			"biotrack_transaction_id": biotrack_employee.get("transactionid"),
			"biotrack_transaction_id_original": biotrack_employee.get("transactionid_original"),
			"sync_with_biotrack": 1,
			"company": biotrack_settings.employee_company or get_default_company(),
			"date_of_birth": date_of_birth,
			"date_of_joining": date_of_joining,
		})

		employee.flags.ignore_mandatory = True
		employee.insert()

		biotrack_employee_list.append(biotrack_employee.get("employee_id"))
		frappe.db.commit()

	except Exception as e:
		make_biotrack_log(title=e.message, status="Error", method="create_employee", message=frappe.get_traceback(),
						  request_data=biotrack_employee, exception=True)

def get_biotrack_employees():
	data = do_request('sync_employee', {'active': 1})

	return data.get('employee') if bool(data.get('success')) else []
