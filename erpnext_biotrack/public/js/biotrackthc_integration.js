frappe.provide("frappe.integration_service");

frappe.integration_service.biotrack_settings = Class.extend({
    init: function (frm) {

    },

    get_scheduler_job_info: function () {
        return {
            "Daily": "Synchrony data from BioTrack on daily basis",
            "Weekly": "Synchrony data from BioTrack on weekly basis"
        }
    },

    get_service_info: function (frm) {
        frappe.call({
            method: "erpnext_biotrack.biotrackthc.doctype.biotrack_settings.biotrack_settings.get_service_details",
            callback: function (r) {
                var integration_service_help = frm.fields_dict.integration_service_help.wrapper;
                $(integration_service_help).empty();
                $(integration_service_help).append(r.message);
            }
        })
    }
});