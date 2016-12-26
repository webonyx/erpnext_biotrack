// Copyright (c) 2016, Webonyx and contributors
// For license information, please see license.txt
frappe.provide("traceability.cultivation");

traceability.cultivation.PlantEntry = frappe.ui.form.Controller.extend({
    refresh: function () {
        erpnext.toggle_naming_series();
        // this.toggle_related_fields(this.frm.doc);
        this.frm.toggle_display("company", false);
    },
    get_plants: function () {
        var me = this, fields = [
            {
                fieldtype: 'Link',
                label: __('Strain'),
                fieldname: 'strain',
                options: 'Strain',
                reqd: 1
            }
        ];
        if (!this.frm.doc.from_plant_room)
            fields.push({
                fieldtype: 'Link',
                label: __('From Plant Room'),
                fieldname: 'from_plant_room',
                options: 'Plant Room'
            });

        var d = new frappe.ui.Dialog({
            title: __("Get Plants"),
            fields: fields
        });

        d.set_primary_action(__('Get'), function () {
            var values = d.get_values();
            if (!values)
                return;

            me.frm.doc.strain = values['strain'];
            me.frm.doc.from_plant_room = values['from_plant_room'];
            me.frm.call({
                doc: me.frm.doc,
                method: "get_plants",
                callback: function (r) {
                    if (!r.exc) refresh_field("plants");
                    d.hide();
                }
            });
        });
        d.show();

        // return this.frm.call({
        //     doc: me.frm.doc,
        //     method: "get_plants",
        //     callback: function (r) {
        //         if (!r.exc) refresh_field("plants");
        //     }
        // });
    },
});

cur_frm.script_manager.make(traceability.cultivation.PlantEntry);

cur_frm.cscript.validate = function (doc, cdt, cdn) {
    cur_frm.cscript.validate_plants(doc);
}

cur_frm.cscript.validate_plants = function (doc) {
    if (!doc.flower) {
        msgprint(__("Please set Flower weight"));
        validated = false;
    }

    var cl = doc.plants || [];
    if (!cl.length) {
        msgprint(__("Plant table can not be blank"));
        validated = false;
    }

    var ple = doc.plants[0];
    var mixedStrain = $.grep(doc.plants, function (p) {
        return p.strain !== ple.strain
    })

    if (mixedStrain.length) {
        msgprint(__("Plants must be same Strain"));
        validated = false;
    }
}

frappe.ui.form.on('Plant Entry Detail', {
    plant_code: function (doc, cdt, cdn) {
        var d = locals[cdt][cdn];
        if (d.plant_code) {
            var args = {
                'plant_code': d.plant_code
            };
            return frappe.call({
                doc: cur_frm.doc,
                method: "get_plant_details",
                args: args,
                callback: function (r) {
                    if (r.message) {
                        var d = locals[cdt][cdn];
                        $.each(r.message, function (k, v) {
                            d[k] = v;
                        });
                        refresh_field("plants");
                    }
                }
            });
        }
    }
})
frappe.ui.form.on('Plant Entry', {
    refresh: function (frm) {

    }
});
