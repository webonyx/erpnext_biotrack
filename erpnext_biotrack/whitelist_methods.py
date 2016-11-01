import frappe
from frappe.desk.reportview import execute, scrub_user_tags, get_stats as frappe_get_stats

@frappe.whitelist()
def get_stats(stats, doctype):
	"""get tag info: exclude disabled Items from stat"""

	if doctype != 'Item':
		return frappe_get_stats(stats, doctype)

	import json
	tags = json.loads(stats)
	stats = {}

	columns = frappe.db.get_table_columns(doctype)
	for tag in tags:
		if not tag in columns: continue
		tagcount = execute(doctype, fields=[tag, "count(*)"],
			filters=["ifnull(`%s`,'')!='' and disabled = 0" % tag], group_by=tag, as_list=True)

		if tag=='_user_tags':
			stats[tag] = scrub_user_tags(tagcount)
		else:
			stats[tag] = tagcount

	return stats