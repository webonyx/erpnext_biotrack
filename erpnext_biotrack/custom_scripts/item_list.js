var settings = $.extend({}, {}, frappe.listview_settings['Item']);
if (settings.add_fields.indexOf('test_result') === -1) {
    settings.add_fields.push('test_result');
}

frappe.listview_settings['Item'] = $.extend({}, settings, {
    get_indicator: function (doc) {
        var indicator;
        if (settings.get_indicator) {
            indicator = settings.get_indicator(doc);
        }

        if (indicator) {
            return indicator;
        } else if (doc.test_result) {
            var indicators = {
                'Failed': 'red',
                'Pending': 'grey',
                'Passed': 'green',
                'Rejected': 'red'
            };
            return [__(doc.test_result), indicators[doc.test_result], "test_result,=," + doc.test_result];
        }
    },

    onload: function (list) {
        if (settings.onload) {
            settings.onload(list);
        }

        list.listview.stats.push("test_result");
        list.listview.stats.push("item_group");

        list.page.add_action_item(__("Create Lot"), function () {
            new_stock_entry('Create Lot');
        });

        list.page.add_action_item(__("Create Product"), function () {
            new_stock_entry('Create Product');
        });

        if (frappe.boot.biotrackthc_sync_down) {
            list.page.add_action_item(__("BioTrackTHC Sync"), function () {
                frappe.call({
                    method: "erpnext_biotrack.biotrackthc.doctype.biotrack_settings.biotrack_settings.sync_now",
                    args: {"doctype": "Item"}
                })
            })
        }
    }
});

function new_stock_entry(conversion) {
    frappe.model.with_doctype('Stock Entry', function () {
        var doc = frappe.model.get_new_doc('Stock Entry');
        doc.purpose = "Material Issue";
        doc.conversion = conversion;
        frappe.set_route('Form', doc.doctype, doc.name);
    })
}