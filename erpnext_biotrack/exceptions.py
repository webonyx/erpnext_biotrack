from __future__ import unicode_literals
import frappe

class BiotrackError(frappe.ValidationError): pass

class BiotrackSetupError(BiotrackError): pass

class BioTrackClientError(BiotrackError): pass