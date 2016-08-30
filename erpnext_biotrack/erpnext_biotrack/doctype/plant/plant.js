// Copyright (c) 2016, Webonyx and contributors
// For license information, please see license.txt

frappe.ui.form.on('Plant', {
    onload: function (frm) {
        console.log(frm)
        if (frm.is_new()) {
            frm.toggle_display("remove_scheduled", false);
            frm.toggle_display("harvest_scheduled", false);
            frm.toggle_display("state", false);
            frm.toggle_display("barcode", false);
            frm.toggle_reqd("barcode", false);
        }

    },
    refresh: function (frm) {
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
