frappe.listview_settings['Item'] = {
    onload: function (DocListView) {
        DocListView.listview.stats.push("item_group");
        DocListView.page.add_action_item(__("New Synchronous Item"), function () {
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
                            filters: {"is_group": 0, "plant_room": 0}
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
                title: __("New Synchronous Item"),
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
    },
    refresh: function (DocListView) {
    }
};
