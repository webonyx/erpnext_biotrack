# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version

app_name = "erpnext_biotrack"
app_title = "ERPNext Traceability"
app_publisher = "Webonyx"
app_description = "Traceability System based on ERPNext"
app_icon = "fa fa-leaf"
app_color = "green"
app_email = "viet@webonyx.com"
app_license = "MIT"

fixtures = [
	{
		"doctype": "Custom Field",
		"filters": [
			["name", "in", (
				# Item
				"Item-strain",
				"Item-is_lot_item",
				"Item-parent_item",
				"Item-plant",
				"Item-plant_entry",
				"Item-test_result",
				"Item-sample_id",
				"Item-is_marijuana_item",
				"Item-bio_last_sync",
				"Item-bio_barcode",
				"Item-bio_remaining_quantity",
				"Item-transaction_id",
				"Item-linking_data",
				"Item-certificate",

				# Item Group
				"Item Group-external_id",
				"Item Group-can_be_collected",

				# Employee
				"Employee-external_id",
				"Employee-external_transaction_id",


				"Warehouse-external_id",
				"Warehouse-external_transaction_id",
				"Warehouse-quarentine",

				# Customer
				"Customer-external_transaction_id",
				"Customer-ubi",
				"Customer-license_no",

				# Delivery Note
				"Delivery Note-external_id",
				"Delivery Note-depart_datetime",
				"Delivery Note-arrive_datetime",

				"Stock Entry-plant",
				"Stock Entry-conversion",
				"Stock Entry-conversion_sec",
				"Stock Entry-product_group",
				"Stock Entry-product_name",
				"Stock Entry-product_item",
				"Stock Entry-waste_item",
				"Stock Entry-lot_group",
				"Stock Entry-lot_item",
				"Stock Entry-conversion_cb",
				"Stock Entry-product_qty",
				"Stock Entry-product_waste",
				"Stock Entry-product_usable",

				"Stock Entry Detail-strain",

				# Supplier
				"Supplier-license_no",

				"Quality Inspection-barcode",
				"Quality Inspection-is_sample",
				"Quality Inspection-employee",
				"Quality Inspection-qa_lab",
				"Quality Inspection-test_result",

				"Quotation Item-test_result",
				"Quotation Item-potency",
				"Quotation Item-thca",

				"Integration Request-action",

				"Plant Room-bio_id",
				"Plant Room-bio_name",
				"Plant Room-bio_transactionid"
			)]
		]
	},
	{
		"doctype": "Role",
		"filters": [
			["name", "in", ("Traceability User", "Traceability Manager")]
		]
	}
]

error_report_email = "viet@webonyx.com"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/erpnext_biotrack/css/erpnext_biotrack.css"
app_include_js = [
	"/assets/erpnext_biotrack/js/erpnext_biotrack.js",
	"/assets/erpnext_biotrack/js/biotrackthc_integration.js",
]

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

integration_services = ["BioTrack"]

extend_bootinfo = [
	"erpnext_biotrack.biotrackthc.bootinfo.boot"
]

# Form custom scripts
doctype_js = {
	"Item": "custom_scripts/item.js",
	"Delivery Note": "custom_scripts/delivery_note.js",
	"Material Request": "custom_scripts/material_request.js",
	"Sales Order": "custom_scripts/sales_order.js",
	"Production Order": "custom_scripts/production_order.js",
	"Purchase Invoice": "custom_scripts/purchase_invoice.js",
	"Purchase Order": "custom_scripts/purchase_order.js",
	"Quotation": "custom_scripts/quotation.js",
	"Stock Entry": "custom_scripts/stock_entry.js",
	"Quality Inspection": "custom_scripts/quality_inspection.js",
}

# List custom scripts
doctype_list_js = {
	"Item": "custom_scripts/item_list.js",
	"Customer": "custom_scripts/customer_list.js",
	"Employee": "custom_scripts/employee_list.js",
	"Supplier": "custom_scripts/supplier_list.js",
	"Quality Inspection": "custom_scripts/quality_inspection_list.js",
	"Warehouse": "custom_scripts/warehouse_list.js"
}

standard_queries = {
	# "Plant": "erpnext_biotrack.traceability.doctype.plant.plant.get_plant_list"
}

# Website user home page (by function)
# get_website_user_home_page = "erpnext_biotrack.utils.get_home_page"

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "erpnext_biotrack.install.before_install"
after_install = "erpnext_biotrack.install.after_install"

biotrack_synced = [
	"erpnext_biotrack.item_utils.item_linking_correction",
	"erpnext_biotrack.item_utils.qa_result_population"
]

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

doc_events = {
	"Item": {
		"validate": "erpnext_biotrack.item_utils.on_validate"
	},
	"Stock Entry": {
		"on_submit": [
			"erpnext_biotrack.stock_entry.on_submit", # for conversion handler
			"erpnext_biotrack.biotrackthc.hooks.stock_entry.call_hook", # for new_inventory sync up
		],
		"get_item_details": "erpnext_biotrack.stock_entry.get_item_details",
		"after_conversion": "erpnext_biotrack.biotrackthc.hooks.stock_entry.call_hook",
	},
	"Quality Inspection": {
		"on_submit": [
			"erpnext_biotrack.quality_inspection.on_submit"
		]
	},
	"File": {
		"on_trash": "erpnext_biotrack.item_utils.remove_certificate_on_trash_file",
	},
	"Plant": {
		"before_submit": "erpnext_biotrack.biotrackthc.hooks.plant.call_hook",
		"before_cancel": "erpnext_biotrack.biotrackthc.hooks.plant.call_hook",
		"on_trash": "erpnext_biotrack.biotrackthc.hooks.plant.call_hook",
		"on_harvest_schedule": "erpnext_biotrack.biotrackthc.hooks.plant.call_hook",
		"on_destroy_schedule": "erpnext_biotrack.biotrackthc.hooks.plant.call_hook"
	},
	"Plant Entry": {
		"before_submit": "erpnext_biotrack.biotrackthc.hooks.plant_entry.call_hook",
		"before_cancel": "erpnext_biotrack.biotrackthc.hooks.plant_entry.call_hook"
	},
	"Plant Room": {
		"after_insert": "erpnext_biotrack.biotrackthc.hooks.plant_room.call_hook",
		"on_update": "erpnext_biotrack.biotrackthc.hooks.plant_room.call_hook",
		"on_trash": "erpnext_biotrack.biotrackthc.hooks.plant_room.call_hook",
	},
}

plant_events = [
	"erpnext_biotrack.biotrackthc.hooks.plant.call_hook"
]

# Scheduled Tasks
# ---------------

scheduler_events = {
	# 	"all": [
	# 		"erpnext_biotrack.tasks.all"
	# 	],
	# "daily": [
	# ],
	"hourly": [
		"erpnext_biotrack.traceability.doctype.plant.plant.destroy_scheduled_plants",
	],
	# "weekly": [
	# ]
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
override_whitelisted_methods = {
	"erpnext.stock.get_item_details.get_item_details": "erpnext_biotrack.item_utils.get_item_details",
	"frappe.desk.reportview.get_stats": "erpnext_biotrack.whitelist_methods.get_stats"
}
