// Copyright (c) 2016, Webonyx and contributors
// For license information, please see license.txt

frappe.provide("erpnext_biotrack.plant");
frappe.ui.form.on('Plant', {
    onload: function (frm) {


    },
    refresh: function (frm) {
        var is_new = frm.is_new();
        frm.toggle_display("remove_scheduled", !is_new);
        frm.toggle_display("harvest_scheduled", !is_new);
        frm.toggle_display("state", !is_new);
        frm.toggle_display("barcode", !is_new);
        frm.toggle_reqd("barcode", !is_new);

        if (!is_new && frappe.model.can_delete('Plant') && frm.doc.state == 'Growing') {
            frm.add_custom_button(__("Undo Plant"), function () {
                frappe.confirm(
                    "System will permanently remove this plant and restore it's source balance",
                    function () {
                        frm.validate_form_action("Delete");
                        erpnext_biotrack.plant.plant_new_undo(frm.doc);
                    },
                    function () {
                    }
                )
            })
                .removeClass('btn-default')
                .addClass('btn-danger')
        }

        frm.fields_dict['source'].get_query = function (doc, cdt, cdn) {
            if (frm.doc.item_group) {
                return {
                    filters: {'item_group': frm.doc.item_group}
                }
            } else {
                return {
                    filters: {'item_group': ["in", frm.get_field('item_group').df.options.split("\n")]}
                }
            }
        };

        frm.fields_dict['warehouse'].get_query = function (doc, cdt, cdn) {
            return {
                filters: {'plant_room': 1}
            }
        };
    }
});

$.extend(erpnext_biotrack.plant, {
    plant_new_undo: function (doc) {
        frappe.call({
            method: 'erpnext_biotrack.erpnext_biotrack.doctype.plant.plant.plant_new_undo',
            args: {name: doc.name},
            callback: function (r) {
                // frappe.set_route('List', 'Plant');
                window.history.back();
            }
        });
    }
});