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
        frm.toggle_reqd("item_group", is_new);
        frm.toggle_reqd("source", is_new);

        erpnext_biotrack.plant.setup_actions(frm);

        function cal_remaining_time(d) {
            var expire_d = moment(d).add(72, "hours");
            var diff = moment(expire_d).diff(moment(), "hours");

            if (diff == 0) {
                diff = moment(expire_d).diff(moment(), "minutes");
                diff += ' minutes'
            } else {
                if (diff < 0) {
                    diff = 0;
                }

                diff += ' hours'
            }

            return diff
        }

        if (frm.doc.remove_scheduled) {
            frm.dashboard.add_comment(
                __("This Plant is scheduled for destroying, <strong>{0}</strong> remaining", [cal_remaining_time(frm.doc.remove_time)]),
                true
            );
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
                filters: {"warehouse_type": 'Plant Room'}
            }
        };
    }
});

$.extend(erpnext_biotrack.plant, {
    setup_actions: function (frm) {
        if (!frm.is_new()) {
            if (!frm.doc.harvest_scheduled) {
                frm.add_custom_button(__("Harvest Schedule"), function () {
                    erpnext_biotrack.plant.harvest_schedule(frm, $(this));
                })
            }

            if (!frm.doc.remove_scheduled) {
                frm.add_custom_button(__("Destroy Schedule"), function () {
                    erpnext_biotrack.plant.destroy_schedule(frm);
                })
            }

            // Actions
            if (frm.doc.harvest_scheduled) {
                frm.add_custom_button(__("Undo Scheduled Harvest"), function () {
                    erpnext_biotrack.plant.harvest_schedule_undo(frm);
                }, 'Actions')
            }

            if (frm.doc.remove_scheduled) {
                frm.add_custom_button(__("Re-Schedule Destroy"), function () {
                    erpnext_biotrack.plant.destroy_schedule(frm);
                }, 'Actions');

                frm.add_custom_button(__("Undo Scheduled Destroy"), function () {
                    erpnext_biotrack.plant.destroy_schedule_undo(frm);
                }, 'Actions')
            }

            if (frappe.model.can_delete('Plant') && frm.doc.state == 'Growing') {
                if (frm.doc.harvest_scheduled || frm.doc.remove_scheduled) {
                    frm.page.get_inner_group_button('Actions')
                        .find('ul').append('<li class="divider"></li>');
                }

                frm.add_custom_button(__("Delete Plant"), function () {
                    frappe.confirm(
                        "System will permanently remove this plant and restore it's source balance",
                        function () {
                            frm.validate_form_action("Delete");
                            erpnext_biotrack.plant.plant_new_undo(frm.doc);
                        },
                        function () {
                        }
                    )
                }, 'Actions');


            }
        }

    },
    plant_new_undo: function (doc) {
        frappe.call({
            doc: doc,
            method: 'undo',
            callback: function (data) {
                window.history.back();
            }
        });
    },
    destroy_schedule: function (frm) {
        var doc = frm.doc,
            fields = [
                {
                    fieldname: 'name', label: 'Plant',
                    fieldtype: 'Data', read_only: 1
                },
                {
                    fieldname: 'reason', label: __('Reason'),
                    fieldtype: 'Select', options: [
                    'Other',
                    'Waste',
                    'Unhealthy or Died',
                    'Infestation',
                    'Product Return',
                    'Mistake',
                    'Spoilage',
                    'Quality Control'
                ]
                },
                {
                    fieldname: 'reason_txt', label: __('Reason detail'),
                    fieldtype: 'Text'
                }
            ],
            dialog;

        if (doc.remove_scheduled) {
            fields.push({
                fieldname: 'override', label: __('Reset Scheduled time'),
                fieldtype: 'Check'
            })
        }

        dialog = new frappe.ui.Dialog({
            title: __('Destroy Scheduler'),
            fields: fields
        });

        dialog.get_field('name').set_input(doc['name']);

        if (doc.remove_scheduled) {
            dialog.get_field('override').set_input(1);
        }

        dialog.set_primary_action(__('Submit'), function () {
            var values = dialog.get_values();
            if (!values) {
                return;
            }

            if (!values.reason) {
                frappe.msgprint({
                    message: __('Please specify a reason'),
                    indicator: 'red',
                    title: 'Error'
                });

                return;
            }

            if (values.reason == 'Other' && !values.reason_txt) {
                frappe.msgprint({
                    message: __('Please input a reason detail'),
                    indicator: 'red',
                    title: 'Error'
                });

                return;
            }

            delete values['name'];
            frappe.call({
                doc: doc,
                method: 'destroy_schedule',
                args: values,
                callback: function (data) {
                    dialog.hide();
                    cur_frm.reload_doc();
                }
            });
        });

        dialog.show();
    },
    harvest_schedule: function (frm, $btn) {
        $btn.attr('disabled', true).text('Scheduling...');
        frappe.call({
            doc: frm.doc,
            method: 'harvest_schedule',
            callback: function (data) {
                cur_frm.reload_doc();
            }
        });
    },
    destroy_schedule_undo: function (frm) {
        frappe.confirm(
            'Please confirm this action',
            function () {
                frappe.call({
                    doc: frm.doc,
                    method: 'destroy_schedule_undo',
                    callback: function (data) {
                        cur_frm.reload_doc();
                    }
                });
            }
        );
    },
    harvest_schedule_undo: function (frm) {
        frappe.confirm(
            'Please confirm this action',
            function () {
                frappe.call({
                    doc: frm.doc,
                    method: 'harvest_schedule_undo',
                    callback: function (data) {
                        cur_frm.reload_doc();
                    }
                });
            }
        );
    },
});