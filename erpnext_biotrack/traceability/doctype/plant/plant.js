// Copyright (c) 2016, Webonyx and contributors
// For license information, please see license.txt

frappe.provide("erpnext_biotrack.plant");

frappe.ui.form.on('Plant', {
    onload: function (frm) {
        frm.set_df_property("from_warehouse", "only_select", true);
    },
    refresh: function (frm) {
        var is_new = frm.is_new();
        frm.toggle_display("qty", (frm.doc.docstatus == 0));
        frm.toggle_display("destroy_scheduled", !is_new);
        frm.toggle_display("harvest_scheduled", !is_new);
        frm.toggle_display("state", !is_new);
        frm.toggle_display("disabled", !is_new);
        frm.toggle_display("source_plant", false);

        erpnext_biotrack.plant.setup_actions(frm);
        erpnext_biotrack.plant.setup_queries(frm);

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
                    __("Plant has been scheduled for destruction. <strong>{0}</strong>", [cal_remaining_time(frm.doc.remove_time)]),
                    true
                );
            }

        }
    },
    validate: function (frm) {
        if ((!frm.doc.source_plant && !frm.doc.item_code) || (frm.doc.source_plant && frm.doc.item_code)) {
            frappe.msgprint({
                'title': __('Validation Error'),
                'message': __('Either Source Plant or Source Item is required.'),
                'indicator': 'red'
            })

            validated = false
        }
    },
    strain: function (frm) {
        erpnext_biotrack.plant.setup_queries(frm);
    },
    item_code: function (frm) {
        if (frm.doc.item_code) {
            erpnext_biotrack.plant.get_source_details(frm, {'item_code': frm.doc.item_code});
        }
    },
    source_plant: function (frm) {
        if (frm.doc.source_plant) {
            erpnext_biotrack.plant.get_source_details(frm, {'source_plant': frm.doc.source_plant});
        }
    }
});

frappe.ui.form.on('Plant', 'before_submit', function (frm) {
    var deferred = $.Deferred();
    if (frm.doc.qty > 5 && frappe.boot.biotrackthc_sync_up) {
        frappe.confirm(
            __('High quantity with BioTrackTHC synchronization enabled would increase network latency. Would you like to continue?'),
            function () {
                deferred.resolve()
            }, function () {
                validated = 0;
                deferred.reject()
            }
        );
    } else {
        deferred.resolve()
    }

    return deferred.promise();
});

$.extend(erpnext_biotrack.plant, {
    get_source_details: function (frm, args) {
        frappe.call({
            method: 'erpnext_biotrack.traceability.doctype.plant.plant.get_source_details',
            args: args,
            callback: function (r) {
                $.each(r.message, function (k, v) {
                    if (v) {
                        frm.doc[k] = v
                    }
                })

                frm.refresh()
            }
        });
    },
    setup_queries: function (frm) {
        frm.fields_dict['source_plant'].get_query = function (doc, cdt, cdn) {
            var filters = {is_mother_plant: 1}
            if (frm.doc.strain) {
                filters['strain'] = frm.doc.strain
            }

            return {
                filters: filters
            }
        };

        frm.fields_dict['item_code'].get_query = function (doc, cdt, cdn) {
            var filters = {is_stock_item: 1, item_group: ["in", frm.get_field('item_group').df.options.split("\n")]}

            if (frm.doc.strain) {
                filters['strain'] = frm.doc.strain
            } else {
                filters['strain'] = ["!=", ""]
            }

            return {
                filters: filters
            }
        };
    },
    setup_actions: function (frm) {
        frm.page.clear_actions_menu();

        if (frm.is_new() || frm.doc.disabled || frm.doc.docstatus != 1) {
            return;
        }

        if (frm.doc.wet_weight && !frm.doc.dry_weight) {
            var $btn = frm.add_custom_button(__('Undo Harvest'), function () {
                $btn.prop('disabled', true);
                frappe.call({
                    doc: frm.doc,
                    method: 'harvest_undo',
                    callback: function (data) {
                        cur_frm.reload_doc();
                    }
                });
            })
        }

        if (!frm.doc.destroy_scheduled) {
            if (frm.doc.state == 'Growing') {
                var harvest_scheduled = frm.get_field('harvest_scheduled'),
                    $btnUndo = harvest_scheduled.$wrapper.find('.btn-undo');

                if (!frm.doc.harvest_scheduled) {
                    $btnUndo.remove()
                    frm.page.add_action_item(__('Harvest Schedule'), function () {
                        erpnext_biotrack.plant.harvest_schedule(frm);
                    });
                } else {
                    if (!$btnUndo.length) {
                        harvest_scheduled.toggle_description(false);
                        var $undo = $('<button class="btn btn-default btn-xs btn-undo">' + __('Undo') + '</button>')
                            .on('click', function () {
                                erpnext_biotrack.plant.harvest_schedule_undo(frm);
                            });
                        harvest_scheduled.$wrapper.find('.checkbox').append($undo);
                    }

                    frm.page.add_action_item(__('Harvest'), function () {
                        erpnext_biotrack.plant.harvest_cure(frm);
                    });
                }


                frm.page.add_action_item(__('Move to Warehouse'), function () {
                    erpnext_biotrack.plant.move_to_inventory(frm);
                })
            } else if (frm.doc.state == 'Drying') {
                frm.page.add_action_item(__('Cure'), function () {
                    erpnext_biotrack.plant.harvest_cure(frm);
                });
            }

        } else {
            frm.add_custom_button(__('Destroy Schedule Undo'), function () {
                erpnext_biotrack.plant.destroy_schedule_undo(frm);
            });

            frm.add_custom_button(__('Destroy Schedule Override'), function () {
                erpnext_biotrack.plant.destroy_schedule(frm);
            });
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
    harvest_schedule: function (frm) {
        frappe.call({
            doc: frm.doc,
            method: 'harvest_schedule',
            callback: function (data) {
                cur_frm.reload_doc();
                frappe.utils.play_sound("submit");
            }
        });
    },
    harvest_cure: function (frm) {
        frappe.model.with_doctype('Plant Entry', function () {
            var doc = frappe.model.get_new_doc('Plant Entry')
            doc.purpose = (frm.doc.state === 'Growing' ? 'Harvest' : 'Cure')
            var row = frappe.model.add_child(doc, 'plants')
            row.plant_code = frm.doc.name
            row.strain = frm.doc.strain

            frappe.set_route('Form', doc.doctype, doc.name)
        })
    },
    move_to_inventory: function (frm) {
        frappe.model.with_doctype('Plant Entry', function () {
            var doc = frappe.model.get_new_doc('Plant Entry')
            doc.purpose = 'Convert';
            var row = frappe.model.add_child(doc, 'plants')
            row.plant_code = frm.doc.name
            row.strain = frm.doc.strain

            frappe.set_route('Form', doc.doctype, doc.name)
        })
    },
    destroy_schedule: function (frm) {
        var doc = frm.doc,
            fields = [
                {
                    fieldname: 'reason', label: __('Choose a reason for scheduling this destruction'),
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

        if (doc.destroy_scheduled) {
            fields.push({
                fieldname: 'override', label: __('Reset Scheduled time'),
                fieldtype: 'Check'
            })
        }

        dialog = new frappe.ui.Dialog({
            title: __('Destruction Notification'),
            fields: fields
        });

        if (doc.destroy_scheduled) {
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
                    frappe.utils.play_sound("submit");
                }
            });
        });

        dialog.show_message('This will initiate the 72 hour waiting period.');
        dialog.message.removeClass('small text-muted');
        dialog.show();
    },

    destroy_schedule_undo: function (frm) {
        frappe.call({
            doc: frm.doc,
            method: 'destroy_schedule_undo',
            callback: function (data) {
                frappe.utils.play_sound("submit");
                cur_frm.reload_doc();
            }
        });
    },
    harvest_schedule_undo: function (frm) {
        var $btn = frm.get_field('harvest_scheduled').$wrapper.find('.btn-undo')
        $btn.attr('disabled', true);
        frappe.call({
            doc: frm.doc,
            method: 'harvest_schedule_undo',
            callback: function (data) {
                frappe.utils.play_sound("submit");
                $btn.remove();
                cur_frm.reload_doc();
            }
        });
    }
});