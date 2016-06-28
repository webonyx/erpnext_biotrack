# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version

app_name = "erpnext_biotrack"
app_title = "ERPNext Biotrack"
app_publisher = "Webonyx"
app_description = "Biotrack connector for ERPNext"
app_icon = "octicon octicon-globe"
app_color = "green"
app_email = "jared@webonyx.com"
app_license = "MIT"

fixtures = [
	{
		"doctype":"Custom Field",
		"filters": [["fieldname", "in", (
			"biotrack_employee_id",
			"biotrack_transaction_id",
			"biotrack_transaction_id_original",
			"sync_with_biotrack"
		)]]
	}
]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/erpnext_biotrack/css/erpnext_biotrack.css"
# app_include_js = "/assets/erpnext_biotrack/js/erpnext_biotrack.js"

# include js, css files in header of web template
# web_include_css = "/assets/erpnext_biotrack/css/erpnext_biotrack.css"
# web_include_js = "/assets/erpnext_biotrack/js/erpnext_biotrack.js"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Website user home page (by function)
# get_website_user_home_page = "erpnext_biotrack.utils.get_home_page"

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "erpnext_biotrack.install.before_install"
# after_install = "erpnext_biotrack.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "erpnext_biotrack.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
#	}
# }

# Scheduled Tasks
# ---------------

scheduler_events = {
# 	"all": [
# 		"erpnext_biotrack.tasks.all"
# 	],
# 	"daily": [
# 		"erpnext_biotrack.tasks.daily"
# 	],
	"hourly": [
		"erpnext_biotrack.tasks.sync_biotrack"
	]
# 	"weekly": [
# 		"erpnext_biotrack.tasks.weekly"
# 	]
# 	"monthly": [
# 		"erpnext_biotrack.tasks.monthly"
# 	]
}

# Testing
# -------

# before_tests = "erpnext_biotrack.install.before_tests"

# Overriding Whitelisted Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "erpnext_biotrack.event.get_events"
# }

