import frappe

def boot(bootinfo):
	settings = frappe.get_doc("BioTrack Settings")

	bootinfo.biotrackthc_enabled = settings.is_enabled()
	bootinfo.biotrackthc_sync_down = settings.is_sync_down_enabled()
	bootinfo.biotrackthc_sync_up = settings.is_sync_up_enabled()