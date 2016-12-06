frappe.ui.form.on('Quality Inspection', {
    refresh: function (frm) {
        frm.events.toggle_sample_fields(frm)
    },
    is_sample: function (frm) {
        frm.events.toggle_sample_fields(frm)
    },
    inspection_type: function (frm) {
        frm.events.toggle_sample_fields(frm)
    },
    toggle_sample_fields: function (frm) {

        frm.toggle_display('employee', (frm.doc.is_sample && frm.doc.inspection_type == "In Process"))
        frm.toggle_reqd('employee', (frm.doc.is_sample && frm.doc.inspection_type == "In Process"))
        frm.toggle_display('verified_by', !frm.doc.is_sample)
        frm.toggle_display('qa_lab', !frm.doc.is_sample)
        frm.toggle_display('test_result', !frm.doc.is_sample)
        frm.toggle_display('specification_details', !frm.doc.is_sample)
    }
});
