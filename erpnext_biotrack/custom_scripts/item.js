frappe.ui.form.on("Item", {
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
                    });

                    dialog.set_title(__('Attach Certificate'));
                });
            }


            if (frm.doc.is_stock_item && (frm.doc.item_group === 'Flower' || frm.doc.item_group === 'Other Plant Material')) {
                frm.add_custom_button(__('Create Lot'), function () {
                    erpnext.item.create_lot(frm.doc);
                });
            }
        }

        erpnext.item.toggle_marijuana_attributes(frm);

    },
    is_marijuana_item: function (frm) {
        erpnext.item.toggle_marijuana_attributes(frm);
    }
});

$.extend(erpnext.item, {
    create_lot: function (doc) {
        frappe.call({
            method: 'erpnext.stock.dashboard.item_dashboard.get_data',
            args: {
                item_code: doc.item_code
            },
            callback: function (r) {
                var data = r.message || [];
                if (data) {
                    open_dialog_form(r.message);
                } else {
                    frappe.msgprint(
                        {
                            title: __('Error'),
                            message: __('Item <strong>{0}</strong> is out of stock', [doc.item_code]),
                            indicator: 'red'
                        }
                    );
                }
            }
        });

        function open_dialog_form(data) {
            frappe.model.with_doctype('Stock Entry', function () {
                var ste = frappe.model.get_new_doc('Stock Entry');
                ste.purpose = "Material Issue";
                ste.conversion = 'Create Lot';
                ste.lot_group = doc.item_group + ' Lot';

                var dialog = new frappe.ui.Dialog({
                    title: __('{0} Lot Creation Tool', [doc.item_group]),
                    fields: [
                        {
                            fieldname: 'item_code', label: __('Item'),
                            fieldtype: 'Link', options: 'Item', read_only: 1, 'default': doc.item_code
                        },
                        {
                            fieldname: 'warehouse', label: __('Warehouse'),
                            fieldtype: 'Select', options: data.map(function (r) {
                                return r.warehouse
                            }
                        ), reqd: 1

                        },
                        {
                            fieldname: 'qty',
                            label: __('Quantity'),
                            reqd: 1,
                            fieldtype: 'Float',
                            depends_on: 'warehouse'
                        },
                        {
                            fieldname: 'rate',
                            label: __('Valuation Rate'),
                            fieldtype: 'Currency',
                            reqd: 1,
                            depends_on: 'warehouse'
                        }
                    ]
                });

                var update_doc = function () {
                    ste.from_warehouse = dialog.get_value('warehouse');
                    ste.items = [];

                    var row = frappe.model.add_child(ste, 'items');
                    row.item_code = dialog.get_value('item_code');
                    row.f_warehouse = dialog.get_value('warehouse');
                    row.qty = dialog.get_value('qty');
                };

                var open_doc = function () {
                    dialog.hide();
                    update_doc();
                    frappe.set_route('Form', 'Stock Entry', ste.name);
                };

                dialog.show();
                var $body = $(dialog.body);

                $body.find('select[data-fieldname="warehouse"]').on("change", function () {
                    var val = $(this).val(), qty = 0, rate, r;
                    if (val) {
                        r = data.filter(function (d) {
                            return d.warehouse === val;
                        });

                        if (r) {
                            qty = r[0].actual_qty;
                            rate = r[0].valuation_rate;
                        }
                    }

                    dialog.get_field('qty').$wrapper.find(".help-box").html(__('Available <strong>{0}</strong>', [qty]));
                    // dialog.set_value('qty', qty);
                    dialog.set_value('rate', rate);
                });

                dialog.set_primary_action(__('Save'), function () {
                    if (dialog.working) return;
                    var data = dialog.get_values();
                    if (data) {
                        update_doc();

                        dialog.working = true;
                        frappe.call({
                            method: "frappe.client.submit",
                            args: {
                                doc: ste
                            },
                            callback: function (r) {
                                dialog.hide();
                                // delete the old doc
                                frappe.model.clear_doc(ste.doctype, ste.name);
                                frappe.ui.form.update_calling_link(r.message.name);
                                cur_frm.reload_doc();
                            },
                            error: function () {
                                open_doc();
                            },
                            always: function () {
                                dialog.working = false;
                            },
                            freeze: true
                        });
                    }
                });

                $('<p style="margin-left: 10px;"><a class="link-open text-muted small">'
                    + __("Add more items or open full form") + '</a></p>')
                    .appendTo($body)
                    .find('.link-open')
                    .on('click', function () {
                        open_doc();
                    });

            });
        }
    },
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
        // frm.toggle_reqd("default_warehouse", frm.doc.is_marijuana_item);

        if (frm.doc.is_marijuana_item || frm.doc.bio_barcode) {
            frm.fields_dict['item_group'].get_query = function (doc, cdt, cdn) {
                return {
                    filters: [["Item Group","docstatus","!=",2], ["Item Group","parent_item_group","=","WA State Classifications"]]
                }
            };
        } else {
            frm.fields_dict['item_group'].get_query = function (doc, cdt, cdn) {
                return {
                    filters: [["Item Group","docstatus","!=",2]]
                }
            };
        }
    }
});