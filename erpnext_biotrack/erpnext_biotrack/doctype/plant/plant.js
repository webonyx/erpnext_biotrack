// Copyright (c) 2016, Webonyx and contributors
// For license information, please see license.txt

frappe.provide("erpnext_biotrack.plant");
frappe.ui.form.on('Plant', {
    refresh: function (frm) {
        var is_new = frm.is_new();
        frm.toggle_display("qty", !is_new);
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
                if (diff < 0) {
                    diff = 0
                } else {
                    diff += ' minutes'
                }
            } else {
                if (diff < 0) {
                    diff = 0;
                } else {
                    diff += ' hours'
                }
            }

            if (diff == 0) {
                diff = '72 hours remaining expired'
            } else {
                diff += ' remaining';
            }

            return diff
        }


        if (frm.doc.remove_scheduled) {
            if (frm.doc.disabled) {
                frm.dashboard.add_comment(
                    __("The Plant had been destroyed"),
                    true
                );
            } else {
                frm.dashboard.add_comment(
                    __("This Plant is scheduled for destruction. <strong>{0}</strong>", [cal_remaining_time(frm.doc.remove_time)]),
                    true
                );
            }

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
    },
    bulk_add: function (frm) {
        frm.toggle_display("qty", frm.doc.bulk_add);
        frm.toggle_reqd("qty", frm.doc.bulk_add);
    }
});

$.extend(erpnext_biotrack.plant, {
    setup_actions: function (frm) {
        frm.page.clear_actions_menu();
        frm.page.clear_secondary_action();
        frm.page.btn_secondary
            .removeClass('btn-primary')
            .addClass('btn-default');

        if (!frm.is_new()) {
            frm.add_custom_button('Related Items', function () {
                frappe.set_route("List", "Item", {plant: frm.doc.name});
            })
        }

        if (frm.doc.disabled) {
            return;
        }

        if (!frm.is_new()) {
            if (!frm.doc.remove_scheduled) {
                frm.page.set_secondary_action('Harvest/Cure', function () {
                    erpnext_biotrack.plant.harvest(frm);
                });

                if (frm.doc.state == 'Growing') {
                    frm.page.add_action_item(__('Move To Inventory'), function () {
                        erpnext_biotrack.plant.move_to_inventory(frm);
                    })
                }

                if (frm.doc.harvest_scheduled) {
                    if (frm.doc.state == 'Growing') {
                        frm.page.add_action_item(__("Undo Scheduled Harvest"), function () {
                            erpnext_biotrack.plant.harvest_schedule_undo(frm);
                        })
                    }
                } else {

                    frm.page.add_action_item(__("Destroy Schedule"), function () {
                        erpnext_biotrack.plant.destroy_schedule(frm);
                    });

                    frm.page.add_action_item(__("Permanently Delete"), function () {
                        frappe.confirm(
                            "System will permanently remove this plant and restore it's source balance to inventory.",
                            function () {
                                frm.validate_form_action("Delete");
                                erpnext_biotrack.plant.plant_new_undo(frm.doc);
                            },
                            function () {
                            }
                        )
                    });
                }


            } else {
                frm.page.add_action_item(__("Undo Scheduled Destruction"), function () {
                    erpnext_biotrack.plant.destroy_schedule_undo(frm);
                });

                frm.page.add_action_item(__("Re-Schedule Destruction"), function () {
                    erpnext_biotrack.plant.destroy_schedule(frm);
                });
            }

            if (frm.doc.harvest_scheduled) {
                frm.page.btn_secondary
                    .removeClass('btn-default')
                    .addClass('btn-primary');
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
    harvest: function (frm) {
        if (!frm.doc.harvest_scheduled) {
            var cf_dialog = frappe.msgprint({
                title: 'Harvest Schedule',
                message: 'You will need to initiate harvest notification before beginning the harvest process. Would you like to' +
                ' do so now?'
            });

            cf_dialog.set_primary_action(__('Yes'), function () {
                cf_dialog.show_loading();
                frappe.call({
                    doc: frm.doc,
                    method: 'harvest_schedule',
                    callback: function (data) {
                        cur_frm.reload_doc();
                        cf_dialog.hide();
                        msg_dialog = null;
                    }
                });
            });

            return;
        }

        var doc = frm.doc,
            fields = [
                {
                    fieldname: 'name', label: 'Barcode', fieldtype: 'Data', read_only: 1, default: doc.name
                },
                {
                    fieldname: 'strain', label: 'Strain', fieldtype: 'Data', read_only: 1, default: doc.strain
                },
                {
                    fieldname: 'uom', label: 'Unit of Measure', fieldtype: 'Select', options: ['Gram'], default: 'Gram'
                },
                {
                    fieldname: 'flower_amount',
                    label: __('Flower {0} Weight', [doc.state == 'Growing' ? 'Wet' : 'Dry']),
                    fieldtype: 'Float',
                    reqd: 1
                },
                {
                    fieldname: 'other_material_amount', label: 'Other Plant Material', fieldtype: 'Float'
                },
                {
                    fieldname: 'waste_amount', label: 'Waste', fieldtype: 'Float'
                }
            ],
            dialog;

        if (doc.state == "Drying") {
            fields.push(
                {
                    fieldname: 'additional_collection', label: 'Additional Collections', fieldtype: 'Check'
                }
            )
        }

        dialog = new frappe.ui.Dialog({
            title: 'Plant ' + (doc.state == 'Growing' ? 'Harvest' : 'Cure'),
            fields: fields,
            onhide: function () {
                cur_frm.reload_doc();
            }
        });

        dialog.set_primary_action(__('Submit'), function () {
            var values = dialog.get_values();
            if (!values) {
                return;
            }

            delete values['name'];
            delete values['strain'];
            delete values['uom']; // discard and use Gram by default

            frappe.call({
                doc: doc,
                method: 'harvest_cure',
                args: values,
                callback: function (data) {
                    if (data.message && data.message.transaction_id) {
                        var confirm_dialog = frappe.msgprint({
                            title: 'Success',
                            message: __(
                                'Plant {0} successfully. If you think this was an accidentally action, click <strong>Undo</strong>',
                                [(doc.state == 'Growing' ? 'harvested' : 'cured')]
                            )
                        });

                        confirm_dialog.set_primary_action(__('Undo'), function () {
                            frappe.call({
                                // doc: frm.doc,
                                // method: 'harvest_cure_undo',
                                // args: data.message,
                                method: 'erpnext_biotrack.erpnext_biotrack.doctype.plant.plant.harvest_cure_undo',
                                args: $.extend({name: doc.name}, data.message),
                                callback: function (data) {
                                    confirm_dialog.hide();
                                    msg_dialog = null
                                }
                            });
                        });

                        confirm_dialog.custom_onhide = function () {
                            dialog.hide();
                        };
                    } else {
                        dialog.hide();
                    }
                }
            });
        });

        dialog.show();
    },
    move_to_inventory: function (frm) {
        var doc = frm.doc,
            fields = [
                {
                    fieldname: 'name', label: 'Plant', fieldtype: 'Data', read_only: 1, default: doc.name
                },
                {
                    fieldname: 'strain', label: 'Strain', fieldtype: 'Data', read_only: 1, default: doc.strain
                }
            ],
            dialog;

        dialog = new frappe.ui.Dialog({
            title: __('Move to Inventory'),
            fields: fields
        });

        dialog.set_primary_action(__('Submit'), function () {
            frappe.call({
                doc: doc,
                method: 'move_to_inventory',
                callback: function (data) {
                    dialog.hide();
                    frappe.set_route('List', 'Plant');
                }
            });
        });

        dialog.show();
    },
    destroy_schedule: function (frm) {
        var doc = frm.doc,
            fields = [
                {
                    fieldname: 'reason', label: __('Please choose a reason for scheduling this destruction'),
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
                    fieldname: 'reason_txt', label: __('Reason Detail'),
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
            title: __('Destruction Schedule'),
            fields: fields
        });

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

        dialog.show_message('This will initiate the 72 hour waiting period.');
        dialog.message.removeClass('small text-muted');
        dialog.show();
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