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
        DocListView.page.add_action_item(__("New Marijuana Item"), function () {
            var doc = frappe.model.get_new_doc(doctype, null, null, true);
            doc.is_marijuana_item = true;

            // Use full page form instead
            frappe.set_route("Form", "Item", doc.name);
            return

            var fields = [
                {
                    fieldname: 'item_name', label: __('Item Name'), reqd: 1, fieldtype: 'Data'
                },
                {
                    fieldname: 'item_group', label: __('Item Group'), reqd: 1, fieldtype: 'Link', options: 'Item Group',
                    get_query: function (doc, cdt, cdn) {
                        return {
                            filters: {'parent_item_group': 'WA State Classifications'}
                        }
                    }
                },
                {
                    fieldname: 'strain', label: __('Strain'), reqd: 1, fieldtype: 'Link', options: 'Strain'
                },
                {
                    fieldname: 'actual_qty', label: __('Quantity'), reqd: 1, fieldtype: 'Float'
                },
                {
                    fieldname: 'default_warehouse',
                    label: __('Warehouse'),
                    reqd: 1,
                    fieldtype: 'Link',
                    options: 'Warehouse',
                    get_query: function (doc, cdt, cdn) {
                        return {
                            filters: {"is_group": 0, "warehouse_type": 'Inventory Room'}
                        }
                    }
                },
                {
                    fieldname: 'plant',
                    label: __('Plant'),
                    fieldtype: 'Link',
                    options: 'Plant'
                }
            ];

            var dialog = new frappe.ui.Dialog({
                title: __("New Marijuana Item"),
                fields: fields
            });

            dialog.fields_dict['item_group'].get_query = function (doc, cdt, cdn) {
                return {
                    filters: {'parent_item_group': 'WA State Classifications'}
                }
            };

            dialog.refresh();
            dialog.set_primary_action(__('Save'), function () {
                if (dialog.working) return;
                var data = dialog.get_values();
                if (data) {
                    dialog.working = true;
                    frappe.call({
                        method: "erpnext_biotrack.item_utils.new_item",
                        args: data,
                        callback: function (r) {
                            dialog.hide();
                            var doc = r.message;
                            frappe.ui.form.update_calling_link(doc.name);
                            frappe.set_route('Form', doc.doctype, doc.name);
                        },
                        error: function () {
                        },
                        always: function () {
                            dialog.working = false;
                        },
                        freeze: true
                    });
                }
            });

            dialog.show();
            $('<div class="text-muted small" style="padding-top: 15px; padding-left: 5px">' +
                '<strong><em>Please be considerate!</em></strong> This action will synchronize with BioTrackTCH database.' +
            '</div>').appendTo(dialog.body);

        }, "octicon octicon-sync");

        DocListView.page.add_action_item(__("Synchronization"), function () {
            frappe.call({
                method: "erpnext_biotrack.tasks.client_sync",
                args: {"doctype": "Item"}
            })
        })
    }
});

