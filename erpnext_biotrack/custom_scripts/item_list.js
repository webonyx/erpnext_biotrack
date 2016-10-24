$.extend(frappe.listview_settings['Item'], {
    add_fields: ["item_name", "stock_uom", "item_group", "image", "variant_of",
		"has_variants", "end_of_life", "disabled", "total_projected_qty", "test_result"],
	filters: [["disabled", "=", "0"]],

	get_indicator: function(doc) {
		if(doc.total_projected_qty < 0) {
			return [__("Shortage"), "red", "total_projected_qty,<,0"];
		} else if (doc.disabled) {
			return [__("Disabled"), "grey", "disabled,=,Yes"];
		} else if (doc.end_of_life && doc.end_of_life < frappe.datetime.get_today()) {
			return [__("Expired"), "grey", "end_of_life,<,Today"];
		} else if (doc.has_variants) {
			return [__("Template"), "blue", "has_variants,=,Yes"];
		} else if (doc.variant_of) {
			return [__("Variant"), "green", "variant_of,=," + doc.variant_of];
		} else if (doc.test_result){
            var indicators = {
                'Failed': 'red',
                'Pending': 'grey',
                'Passed': 'green',
                'Rejected': 'red'
            };
		    return [__(doc.test_result), indicators[doc.test_result], "test_result,=," + doc.test_result];
        }
	},

    onload: function (DocListView) {
        DocListView.listview.stats.push("test_result");
        DocListView.listview.stats.push("item_group");

        DocListView.page.add_action_item(__("Create Lot"), function () {
            var doc = frappe.model.get_new_doc("Stock Entry");
            doc.purpose = "Material Issue";
            doc.conversion = 'Create Lot';
            doc.posting_date = frappe.datetime.get_today();
            doc.posting_time = frappe.datetime.now_time();
            frappe.set_route("Form", "Stock Entry", doc.name);
        });

        DocListView.page.add_action_item(__("Create Product"), function () {
            var doc = frappe.model.get_new_doc("Stock Entry");
            doc.purpose = "Material Issue";
            doc.conversion = 'Create Product';
            doc.posting_date = frappe.datetime.get_today();
            doc.posting_time = frappe.datetime.now_time();
            frappe.set_route("Form", "Stock Entry", doc.name);
        });

        DocListView.page.add_action_item(__("Synchronization"), function () {
            frappe.call({
                method: "erpnext_biotrack.tasks.client_sync",
                args: {"doctype": "Item"}
            })
        })
    }
});

