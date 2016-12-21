frappe.listview_settings['Plant'] = {
    add_fields: ['disabled', 'posting_date', 'destroy_scheduled'],
    filters: [["disabled", "=", "No"]],
    get_indicator: function (doc) {
        if (doc.disabled) {
            return [__("Destroyed"), "grey", "disabled,=,Yes"];
        } else if (doc.destroy_scheduled) {
            return [__("Destroy Scheduled"), "orange", "destroy_scheduled,=,Yes"];
        } else {
            return [this.calculate_time_in_room(doc.posting_date), "green", "disabled,=,No"];
        }
    },

    onload: function (list) {
        list.listview.stats.push("state");
        list.listview.stats.push("plant_room");

        if (frappe.boot.biotrackthc_sync_down) {
            list.page.add_action_item(__("BioTrackTHC Sync"), function () {
                frappe.call({
                    method: "erpnext_biotrack.biotrackthc.doctype.biotrack_settings.biotrack_settings.sync_now",
                    args: {"doctype": "Plant"}
                })
            }, true)
        }
    },
    refresh: function (list) {
        if (!list.list_header) {
            return
        }

        this.init_room_moving(list)
    },

    init_room_moving: function (list) {
        if (list.init_room_moving) {
            return
        }

        list.init_room_moving = true;
        var me = this;

        if (list.can_delete || list.listview.settings.selectable) {
            list.list_header.find(".list-select-all").on("click", function () {
                me.toggle_move(list);
            });

            list.$page.on("click", ".list-delete", function (event) {
                me.toggle_move(list);
            });

            // after move, hide Move button
            list.wrapper.on("render-complete", function () {
                me.toggle_move(list);
            });
        }

    },
    toggle_move: function (list) {
        var me = this;
        var no_of_checked_items = list.$page.find(".list-delete:checked").length,
            $btn = list.page.actions.find('.btn-move'), added = $btn.length;

        if (no_of_checked_items && !added) {
            var $link = list.page.add_action_item(__("Move"), function () {
                me.move_plant(list);
            });

            $link.parent().addClass('user-action btn-move');
        } else {
            if (added && !no_of_checked_items) {
                $btn.remove();
            }
        }
    },
    move_plant: function (list) {
        var checked_items = $.grep(list.get_checked_items(), function (d) {
            return d.disabled === 0;
        });

        if (!checked_items.length) {
            frappe.msgprint(
                {
                    title: __('No Plant'),
                    message: __('Please select at least one active Plant to move.'),
                    indicator: 'red'
                }
            );
            return;
        }

        var dialog = new frappe.ui.Dialog({
            title: __('Room Moving'),
            fields: [
                {
                    fieldname: 'target_plant_room', label: __('Target Room'),
                    fieldtype: 'Link', options: 'Plant Room', reqd: 1

                }
            ]
        });

        dialog.set_primary_action(__('Move'), function () {
            list.set_working(true);
            var target = dialog.get_value('target_plant_room'),
                items = $.map($.grep(checked_items, function (d) {
                    return d.plant_room !== target;
                }), function (d, i) {
                    return d.name
                });

            if (!items.length) {
                frappe.msgprint(
                    {
                        title: __('Invalid Room'),
                        message: __('Please select a room where at least one selected Plant is not in.'),
                        indicator: 'red'
                    }
                );

                return;
            }

            return frappe.call({
                method: "erpnext_biotrack.traceability_system.doctype.plant.plant.move",
                freeze: true,
                args: {
                    items: items,
                    target: target
                },
                callback: function (r) {
                    list.$page.find('.list-select-all').prop("checked", false);
                    frappe.utils.play_sound("delete");
                    list.set_working(false);
                    list.dirty = true;
                    dialog.hide();
                    list.refresh();
                }
            });
        });

        dialog.show();
    },
    calculate_time_in_room: function (posting_date) {
        var diff = frappe.datetime.get_diff(frappe.datetime.get_today(), posting_date);
        if (diff == 0) {
            return comment_when(posting_date);
        }

        if (diff == 1) {
            return __('Yesterday')
        }

        if (diff == 2) {
            return __('2 days ago')
        }

        return diff + ' days';
    }
};
