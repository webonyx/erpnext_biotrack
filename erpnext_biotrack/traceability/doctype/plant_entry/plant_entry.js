// Copyright (c) 2016, Webonyx and contributors
// For license information, please see license.txt
frappe.provide("traceability.cultivation");

traceability.cultivation.PlantEntry = frappe.ui.form.Controller.extend({
    onload: function () {
    },
    refresh: function () {
        erpnext.toggle_naming_series();
        // this.toggle_related_fields(this.frm.doc);
        this.frm.toggle_display("company", false);
        this._toggle_related_fields()
    },
    validate: function (doc) {
        if (doc.purpose !== 'Convert' && !doc.flower) {
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
    },
    purpose: function () {
        this._toggle_related_fields()
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
    },
    _toggle_related_fields: function () {
        var convert = this.frm.doc.purpose === 'Convert';
        this.frm.toggle_display("details_section", !convert);
        this.frm.toggle_reqd("flower", !convert);
    }
});

cur_frm.script_manager.make(traceability.cultivation.PlantEntry);

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
    onload: function (frm) {
        if (frm.doc.__islocal) {
            if (!frm.doc.warehouse) {
                frappe.call({
                    method: "erpnext_biotrack.traceability.doctype.traceability_settings.traceability_settings.get_default_warehouse",
                    callback: function (r) {
                        if (!r.exe) {
                            frm.set_value("target_warehouse", r.message.cultivation_warehouse);
                        }
                    }
                });
            }
        }
    },
    refresh: function (frm) {

    }
});
