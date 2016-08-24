
frappe.ui.form.on("Item", {
    onload: function (frm) {

        frm.fields_dict['default_warehouse'].get_query = function (doc, cdt, cdn) {
            return {
                filters: {"is_group": 0, "plant_room": 0}
            }
        };

        frm.fields_dict['item_group'].get_query = function (doc, cdt, cdn) {
            return {
                filters: {'parent_item_group': 'WA State Classifications'}
            }
        };

    },

    refresh: function (frm) {
        if (frm.doc.is_stock_item) {
            var $btn = frm.add_custom_button(__("Sub Lot/Batch"), function () {
                frappe.call({
                    method: 'erpnext.stock.doctype.stock_reconciliation.stock_reconciliation.get_stock_balance_for',
                    args: {
                        item_code: frm.doc['item_code'],
                        warehouse: frm.doc['default_warehouse'],
                        posting_date: null,
                        posting_time: null
                    },
                    callback: function (r) {
                        var actual_qty = r.message.qty;
                        if (actual_qty) {
                            erpnext.item.clone_item(frm.doc, actual_qty, r.message.rate)
                        } else {
                            $btn.prop('disabled', true);
                        }
                    }
                });

            })
        }
    }
});

$.extend(erpnext.item, {
    clone_item: function (doc, actual_qty, rate) {
        var dialog = new frappe.ui.Dialog({
            title: __('Sub Lot/Batch'),
            fields: [
                {
                    fieldname: 'item_code', label: __('Item'),
                    fieldtype: 'Link', options: 'Item', read_only: 1
                },
                {
                    fieldname: 'default_warehouse', label: __('Warehouse'),
                    fieldtype: 'Link', options: 'Warehouse', read_only: 1
                },

                {
                    fieldname: 'qty', label: __('Quantity'), reqd: 1,
                    fieldtype: 'Float', description: __('Available <strong>{0}</strong>', [actual_qty])
                },
                { fieldname: 'rate', label: __('Rate'), fieldtype: 'Currency', reqd: 1 }
            ]
        });
        dialog.show();

        dialog.get_field('item_code').set_input(doc['item_code']);
        dialog.get_field('default_warehouse').set_input(doc['default_warehouse']);

        dialog.get_field('rate').set_value(rate);
        dialog.get_field('rate').refresh();

        dialog.set_primary_action(__('Submit'), function () {
            var values = dialog.get_values();
            if (!values) {
                return;
            }
            if (values.qty >= actual_qty) {
                frappe.msgprint({
                    message: __('Quantity must be less than  {0}', [actual_qty]),
                    indicator: 'red',
                    title: 'Error'
                });
                return;
            }

            frappe.call({
                method: 'erpnext_biotrack.item_utils.clone_item',
                args: values,
                callback: function (r) {
                    frappe.show_alert(__('Item {0} created',
                        ['<a href="#Form/Item/' + r.message.item_name + '">' + r.message.item_name + '</a>']));
                    dialog.hide();
                    cur_frm.reload_doc();
                }
            });
        });

        $('<p style="margin-left: 10px;"></p>').appendTo(dialog.body);
    }
});