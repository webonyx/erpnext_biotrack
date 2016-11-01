import frappe
from frappe.utils.data import today, nowtime

inter_product_sources = [ "Flower Lot", "Other Material Lot" ]
inter_products = [ "Bubble Hash", "CO2 Hash Oil", "Food Grade Solvent Extract",
					   "Hash", "Hydrocarbon Wax", "Infused Cooking Oil", "Infused Dairy Butter or Fat in Solid Form",
					   "Kief", "Marijuana Mix" ]

end_product_sources = [ "Hydrocarbon Wax", "Food Grade Solvent Extract", "CO2 Hash Oil" ]
end_products = [ "Liquid Marijuana Infused Edible", "Marijuana Extract for Inhalation", "Marijuana Infused Topicals",
					 "Marijuana Mix Infused", "Solid Marijuana Infused Edible", "Suppository",
					 "Tincture", "Transdermal Patch", "Usable Marijuana", "Sample Jar"]

flower_products = ["Marijuana Mix Infused", "Usable Marijuana", "Sample Jar"]

@frappe.whitelist()
def available_products():
	available_groups = []

	def get_item_count(filters):
		filters.update({"is_stock_item": 1, "disabled": 0})
		conditions, values = frappe.db.build_conditions(filters)

		end_of_life = """(tabItem.end_of_life > %(today)s or ifnull(tabItem.end_of_life, '0000-00-00')='0000-00-00')""" % {"today": today()}
		return frappe.db.sql("""select count(*)
						from `tabItem`
						where %s and %s"""
							 % (end_of_life, conditions), values)[0][0]

	if get_item_count({"item_group": ["in", inter_product_sources]}):
		available_groups += inter_products

	if get_item_count({"item_group": ["in", end_product_sources]}):
		available_groups += end_products

	if get_item_count({"item_group": "Flower Lot"}):
		available_groups += flower_products

	return list(set(available_groups))


@frappe.whitelist()
def lookup_product_sources(product):
	sources = []
	if product in inter_products:
		sources += inter_product_sources

	if product in end_products:
		sources += end_product_sources

	if product in flower_products:
		sources.append("Flower Lot")

	return list(set(sources))


def get_available_qty(args, order="desc", limit=1, debug=False):
	"""get stock ledger entries filtered by specific posting datetime conditions"""

	conditions = "timestamp(posting_date, posting_time) <= timestamp(%(posting_date)s, %(posting_time)s)"

	if not args.get("posting_date"):
		args["posting_date"] = today()
	if not args.get("posting_time"):
		args["posting_time"] = nowtime()

	result = frappe.db.sql("""select qty_after_transaction available_qty from `tabStock Ledger Entry` sle
		inner join `tabItem` i on i.name = sle.item_code
		where warehouse = %%(warehouse)s
		and item_group = %%(item_group)s
		and %(conditions)s
		and ifnull(is_cancelled, 'No')='No'
		order by timestamp(posting_date, posting_time) %(order)s, sle.name %(order)s
		%(limit)s""" % {
			"conditions": conditions,
			"limit": limit and "limit {0}".format(limit) or "",
			"order": order
		}, args, as_dict=1, debug=debug)

	f = result and result[0] or {}
	return f.get("available_qty", 0)