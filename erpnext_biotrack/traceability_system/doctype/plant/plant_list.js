frappe.listview_settings['Plant'] = {
    add_fields: ['disabled', 'posting_date', 'harvest_scheduled', 'destroy_scheduled'],
    filters: [["disabled", "=", "No"]],
    get_indicator: function (doc) {
        if (doc.disabled) {
            return [__("Destroyed"), "grey", "disabled,=,Yes"];
        } else if (doc.destroy_scheduled) {
            return [__("Destroy Scheduled"), "orange", "destroy_scheduled,=,Yes"];
        } else if (doc.harvest_scheduled) {
            return [__("Harvest Ready"), "orange", "harvest_scheduled,=,Yes"];
        } else {
            return [this.calculate_time_in_room(doc.posting_date), "green", "disabled,=,No"];
        }
    },

    init: function (list) {
        console.log(list);
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

        list.get_plants = function (returnIf) {
            return $.grep(this.get_checked_items(), returnIf);
        }

        list.get_plants_to_move = function () {
            return this.get_plants(function (d) {
                return d.docstatus === 1 && d.disabled === 0;
            });
        }

        list.get_plants_for_harvest_schedule = function () {
            return this.get_plants(function (d) {
                return d.docstatus === 1 && d.disabled === 0 && d.destroy_scheduled === 0 && d.harvest_scheduled === 0;
            });
        }

        list.get_plants_for_harvest = function () {
            return this.get_plants(function (d) {
                return d.docstatus === 1 && d.disabled === 0 && d.destroy_scheduled === 0 && d.harvest_scheduled === 1;
            });
        }

        list.get_plants_to_destroy = function () {
            return this.get_plants(function (d) {
                return d.docstatus === 1 && d.disabled === 0 && d.destroy_scheduled === 0;
            });
        }

        function add_action(label, callback, cls) {
            var $a = list.page.add_action_item(__(label), function () {
                if (!list.page.actions.find('.' + cls).hasClass('disabled')) {
                    callback(list);
                }
            });

            $a.parent().addClass(cls + ' plant-action disabled');
        }

        add_action(__('Move'), this.move_plant, 'pl-move');
        add_action(__('Harvest'), this.harvest, 'pl-harvest');
        add_action(__('Convert'), this.convert, 'pl-convert');
        add_action(__('Harvest Schedule'), this.harvest_schedule, 'pl-harvest-schedule');
        add_action(__('Destroy Schedule'), this.destroy_schedule, 'pl-destroy-schedule');
    },
    refresh: function (list) {
        if (!list.list_header) {
            return
        }

        this.init_actions(list)
    },

    init_actions: function (list) {
        if (list.init_actions) {
            return
        }

        list.init_actions = true;
        var me = this;

        if (list.can_delete || list.listview.settings.selectable) {
            list.list_header.find(".list-select-all").on("click", function () {
                me.toggle_actions(list);
            });

            list.$page.on("click", ".list-delete", function (event) {
                me.toggle_actions(list);
            });

            // after move, hide Move button
            list.wrapper.on("render-complete", function () {
                me.toggle_actions(list);
            });
        }

    },
    toggle_actions: function (list) {
        function toggle_action(sel, plants) {
            var bool = plants.length ? false : true;
            list.page.actions.find(sel).toggleClass('disabled', bool);
        }

        toggle_action('.pl-move', list.get_plants_to_move());
        toggle_action('.pl-harvest-schedule', list.get_plants_for_harvest_schedule());
        toggle_action('.pl-destroy-schedule', list.get_plants_to_destroy());
        toggle_action('.pl-harvest', list.get_plants_for_harvest());
    },
    build_preview_table: function (plants, list) {
        var rows;
        if (list) {
            rows = $.map(plants, function (p) {
                return '<li>' +
                    '<a class="grey" href="#Form/Plant/' + p.name + '" data-doctype="Plant">' + p.strain + '</a>' +
                    '</li>'
            });

            return '<ol>' + rows.join('') + '</ol>'
        }

        var i = 1; rows = plants.map(function (p) {
            return '<div class="grid-row" data-idx="1">' +
                '<div class="row">' +
                '<div class="row-index col col-xs-1">' + i++ + '</div>' +
                '<div class="col grid-static-col col-xs-11 ">' +
                '<div class="static-area text-ellipsis">' +
                '<a class="grey" href="#Form/Plant/' + p.name + '" data-doctype="Plant">' + p.strain + '</a>' +
                '</div>' +
                '</div>' +
                '</div>' +
                '</div>'
        });

        return '<div style="max-height: 200px; overflow-y: scroll">' +
            '<div class="form-grid">' +
            '<div class="grid-heading-row"> ' +
            '<div class="grid-row"><div class="row">' +
            '<div class="row-index col col-xs-1">&nbsp;</div>' +
            '<div class="col grid-static-col col-xs-11"><div class="static-area text-ellipsis">Plant Name</div></div>' +
            '</div>' +
            '</div>' +
            '</div>' +
            '<div class="grid-body"> ' +
            '<div class="rows">' + rows.join('') + '</div>' +
            '</div>' +
            '</div>' +
            '</div>'
    },
    move_plant: function (list) {
        var me = this, checked_items = list.get_plants_to_move();

        if (!checked_items.length) {
            return;
        }

        var html = frappe.listview_settings.Plant.build_preview_table(checked_items, true);
        var dialog = new frappe.ui.Dialog({
            title: __('Room Move'),
            fields: [
                {
                    fieldname: 'target_plant_room', label: __('Target Room'),
                    fieldtype: 'Link', options: 'Plant Room', reqd: 1

                }
                , {
                    fieldname: 'plants', label: __('Target Room'),
                    fieldtype: 'HTML', options: html

                }
            ]
        });

        dialog.set_primary_action(__('Move'), function () {
            list.set_working(true);
            var target = dialog.get_value('target_plant_room'),
                items = $.grep(checked_items, function (d) {
                    return d.plant_room !== target;
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

            frappe.call({
                method: "erpnext_biotrack.traceability_system.doctype.plant.plant.move",
                freeze: true,
                args: {
                    items: $.map(items, function (d, i) {
                        return d.name
                    }),
                    target: target
                },
                callback: function (r) {
                    dialog.hide();
                    // me variable did not work???
                    frappe.listview_settings.Plant.refresh_list(list);
                }
            });
        });

        dialog.show();
    },
    harvest_schedule: function (list) {
        var checked_items = list.get_plants_for_harvest_schedule();
        if (!checked_items.length) {
            return
        }

        var html = frappe.listview_settings.Plant.build_preview_table(checked_items, true);
        var dialog = new frappe.ui.Dialog({
            title: __('Harvest Schedule'),
            fields: [
                {
                    fieldname: 'plants',
                    fieldtype: 'HTML', options: html

                }
            ]
        });

        dialog.set_primary_action(__('Schedule'), function () {
            list.set_working(true);
            frappe.call({
                method: "erpnext_biotrack.traceability_system.doctype.plant.plant.harvest_schedule",
                freeze: true,
                args: {
                    items: $.map(checked_items, function (d, i) {
                        return d.name
                    })
                },
                callback: function (r) {
                    dialog.hide();
                    frappe.listview_settings.Plant.refresh_list(list);
                }
            });
        });

        dialog.show();
    },
    harvest: function (list) {
        var checked_items = list.get_plants_for_harvest();
        if (!checked_items.length) {
            return
        }

        frappe.model.with_doctype('Plant Entry', function () {
            var doc = frappe.model.get_new_doc('Plant Entry');
            doc.purpose = "Harvest";
            checked_items.forEach(function (d) {
                var row = frappe.model.add_child(doc, 'plants');
                row.plant_code = d.name;
                row.strain = d.strain;
            });

            frappe.set_route('Form', doc.doctype, doc.name);
        })
    },
    destroy_schedule: function (list) {
        var checked_items = list.get_plants_to_destroy();

        if (!checked_items.length) {
            return
        }

        var html = frappe.listview_settings.Plant.build_preview_table(checked_items, true);
        var dialog = new frappe.ui.Dialog({
            title: __('Destroy Schedule'),
            fields: [
                {
                    fieldname: 'plants',
                    fieldtype: 'HTML', options: html

                }
            ]
        });

        dialog.set_primary_action(__('Schedule'), function () {
            list.set_working(true);
            frappe.call({
                method: "erpnext_biotrack.traceability_system.doctype.plant.plant.destroy_schedule",
                freeze: true,
                args: {
                    items: $.map(checked_items, function (d, i) {
                        return d.name
                    })
                },
                callback: function (r) {
                    dialog.hide();
                    frappe.listview_settings.Plant.refresh_list(list);
                }
            });
        });

        dialog.show();
    },
    refresh_list: function (list) {
        frappe.utils.play_sound("submit");

        list.$page.find('.list-select-all').prop("checked", false);
        list.set_working(false);
        list.dirty = true;
        list.refresh();
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
