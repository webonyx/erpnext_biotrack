from __future__ import unicode_literals
import frappe

class BiotrackError(frappe.ValidationError): pass
class BiotrackSetupError(frappe.ValidationError): pass