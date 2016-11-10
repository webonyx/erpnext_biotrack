frappe.ui.form.on("Item", {
    onload: function (frm) {
        frm.fields_dict['item_group'].get_query = function (doc, cdt, cdn) {
            return {
                filters: {'parent_item_group': 'WA State Classifications'}
            }
        };
    },

    refresh: function (frm) {
        if (!frm.is_new()) {
            // Download certificate button
            if (frm.doc.certificate) {
                var file_url = frm.attachments.get_file_url({file_url: frm.doc.certificate});
                file_url = frappe.urllib.get_full_url(file_url);
                $('<a class="btn btn-default btn-xs"' +
                    ' href="' + file_url + '"' +
                    ' target="_blank" style="margin-left: 10px;">' +
                    '<span class="text-muted octicon octicon-file-pdf" aria-hidden="true"></span> ' + __("Download Certificate") + '</a>')
                    .appendTo(frm.page.inner_toolbar);
            }

            // Only Attach Certificate to parent Item
            if (!frm.doc.parent_item) {
                frm.add_custom_button(__("Attach Certificate"), function () {
                    var dialog = frappe.ui.get_upload_dialog({
                        args: {
                            from_form: 1,
                            doctype: frm.doctype,
                            docname: frm.docname
                        },
                        callback: function (attachment, r) {
                            frm.set_value('certificate', attachment.file_url);
                            frm.save('Save');
                        }
                    })

                    dialog.set_title(__('Attach Certificate'));
                });
            }


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
                                frappe.msgprint(
                                    {
                                        message: __("Qty not available for <strong>{0}</strong> in warehouse <strong>{1}</strong>. <br><br>Available qty is <strong>0</strong>", [frm.doc['item_name'], frm.doc['default_warehouse']]),
                                        title: "Insufficient Stock",
                                        indicator: 'red'
                                    }
                                );
                                $btn.prop('disabled', true);
                            }
                        }
                    });

                })
            }
        }

        erpnext.item.toggle_marijuana_attributes(frm);

    },
    is_marijuana_item: function (frm) {
        erpnext.item.toggle_marijuana_attributes(frm)
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
                    fieldname: 'qty',
                    label: __('Quantity'),
                    reqd: 1,
                    fieldtype: 'Float',
                    description: __('Default Unit of Measure <strong>{0}</strong>. Available <strong>{1}</strong>', [doc.stock_uom, actual_qty])
                },
                {fieldname: 'rate', label: __('Valuation Rate'), fieldtype: 'Currency', reqd: 1}
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

        $('<div class="text-muted small" style="padding-top: 15px; padding-left: 5px">' +
            '<strong><em>Please be considerate!</em></strong> This action will synchronize with BioTrackTCH database.' +
            '</div>').appendTo(dialog.body);
    },
    toggle_marijuana_attributes: function (frm) {
        if (frm.doc.__islocal && frm.doc.is_marijuana_item) {
            frm.set_value("stock_uom", 'Gram');
        }

        frm.toggle_display("is_marijuana_item", frm.doc.__islocal);
        frm.toggle_reqd("strain", frm.doc.is_marijuana_item);
        frm.toggle_reqd("default_warehouse", frm.doc.is_marijuana_item);

        frm.toggle_display("actual_qty", frm.doc.is_marijuana_item);
        frm.toggle_reqd("actual_qty", frm.doc.is_marijuana_item);
        frm.toggle_display("barcode", !frm.doc.__islocal || (frm.doc.__islocal && !frm.doc.is_marijuana_item));

    }
});