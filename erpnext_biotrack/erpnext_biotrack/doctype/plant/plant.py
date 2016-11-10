# -*- coding: utf-8 -*-
# Copyright (c) 2015, Webonyx and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, datetime
from erpnext.stock.utils import get_stock_balance
from erpnext_biotrack.biotrackthc import call as biotrackthc_call
from erpnext_biotrack.biotrackthc.client import BioTrackClientError
from erpnext_biotrack.biotrackthc.inventory_room import get_default_warehouse
from erpnext_biotrack.item_utils import get_item_values, make_item
from frappe.desk.reportview import build_match_conditions
from frappe.utils.data import get_datetime_str, DATETIME_FORMAT, cint, now, flt, add_to_date
from frappe.model.document import Document
from erpnext_biotrack.erpnext_biotrack.doctype.strain import find_strain
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from frappe.utils.background_jobs import enqueue

removal_reasons = {
    0: 'Other',
    1: 'Waste',
    2: 'Unhealthy or Died',
    3: 'Infestation',
    4: 'Product Return',
    5: 'Mistake',
    6: 'Spoilage',
    7: 'Quality Control'
}


class Plant(Document):
    def before_insert(self):
        if self.qty:
            item = frappe.get_doc("Item", self.source)
            qty = get_stock_balance(item.item_code, item.default_warehouse)
            if qty < self.qty:
                frappe.throw("The provided quantity <strong>{0}</strong> exceeds stock balance. "
                             "Stock balance remaining <strong>{1}</strong>".format(self.qty, qty))

        if not self.barcode:
            self.biotrack_sync_up()

    def after_insert(self):
        if frappe.flags.in_import or frappe.flags.in_test:
            return

        source_item = frappe.get_doc("Item", self.get("source"))
        make_stock_entry(item_code=source_item.name, source=source_item.default_warehouse, qty=1)

        if self.bulk_add and self.qty > 1:
            frappe.db.commit()
            enqueue(bulk_clone, name=self.name)

    def on_trash(self):
        # able to delete new Plants
        if self.state == "Growing" or not self.harvest_scheduled:
            return

        if not self.remove_scheduled:
            frappe.throw("Plant can not be deleted directly. Please schedule for destruction first")

        if not self.disabled:
            frappe.throw("Plant can only be deleted once destroyed")

    def biotrack_sync_up(self):
        if frappe.flags.in_import or frappe.flags.in_test:
            return

        warehouse = frappe.get_doc("Warehouse", self.get("warehouse"))
        location = frappe.get_value("BioTrack Settings", None, "location")

        result = biotrackthc_call("plant_new", {
            "room": warehouse.external_id,
            "quantity": 1,
            "strain": self.get("strain"),
            "source": self.get("source"),
            "mother": cint(self.get("is_mother")),
            "location": location
        })

        self.set("barcode", result.get("barcode_id")[0])

    def biotrack_sync_down(self, data):
        if not (frappe.flags.force_sync or False) and self.get("transaction_id") == data.get("transactionid"):
            frappe.db.set_value("Plant", self.name, "last_sync", now(), update_modified=False)
            return

        plant_room = frappe.get_doc("Plant Room", {"external_id": data.get("room")})
        properties = {
            "strain": find_strain(data.get("strain")),
            "warehouse": plant_room.get("name") if plant_room else "",
            "is_mother_plant": cint(data.get("mother")),
            "remove_scheduled": cint(data.get("removescheduled")),
            "transaction_id": cint(data.get("transactionid")),
            "last_sync": now(),
            "disabled": 0,
        }

        item_values = get_item_values(data.get("parentid"), ["name", "item_group"])
        if item_values:
            properties["source"], properties["item_group"] = item_values

        if not self.get("birthdate"):
            if isinstance(self.get("creation"), basestring):
                properties["birthdate"] = self.get("creation")
            else:
                properties["birthdate"] = self.get("creation").strftime(DATETIME_FORMAT)

        if properties["remove_scheduled"]:
            remove_datetime = datetime.datetime.fromtimestamp(cint(data.get("removescheduletime")))
            properties["remove_time"] = get_datetime_str(remove_datetime)

            if data.get("removereason"):
                properties["remove_reason"] = data.get("removereason")

        state = int(data.get("state"))
        properties["state"] = "Drying" if state == 1 else ("Cured" if state == 2 else "Growing")

        self.update(properties)
        self.flags.ignore_mandatory = True
        self.save(ignore_permissions=True)

    @Document.whitelist
    def undo(self):
        biotrackthc_call("plant_new_undo", {
            "barcodeid": [self.name],
        })

        # Restore Item source balance
        item = frappe.get_doc("Item", self.get("source"))
        make_stock_entry(item_code=item.name, target=item.default_warehouse, qty=1)
        self.delete()

    @Document.whitelist
    def harvest_cure(self, flower_amount, other_material_amount=None, waste_amount=None, additional_collection=None):
        if self.disabled:
            frappe.throw("Plant <strong>{}</strong> is not available for harvesting.")

        if self.remove_scheduled:
            frappe.throw("Plant <strong>{}</strong> is currently scheduled for destruction and cannot be harvested.")

        amount_map = {
            6: flt(flower_amount),
            9: flt(other_material_amount),
            27: flt(waste_amount),
        }

        weights = [
            {
                "amount": amount_map[6],
                "invtype": 6,
                "uom": "g"
            }
        ]

        if other_material_amount:
            weights.append({
                "amount": amount_map[9],
                "invtype": 9,
                "uom": "g"
            })

        if waste_amount:
            weights.append({
                "amount": amount_map[27],
                "invtype": 27,
                "uom": "g"
            })

        data = {
            'barcodeid': self.name,
            'collectadditional': cint(additional_collection),
            'weights': weights
        }

        action = "plant_cure" if self.state == "Drying" else "plant_harvest"
        flower_weight = amount_map[6]

        if action == "plant_harvest":
            self.wet_weight = flower_weight
        else:
            self.dry_weight = flt(self.dry_weight) + flower_weight
            if self.dry_weight > self.wet_weight:
                frappe.throw(
                    "The provided dry weight <strong>{0}</strong> exceeds the previous wet weight <strong>{1}</strong>.".
                    format(self.dry_weight, self.wet_weight), title="Error")

            data["location"] = frappe.get_value("BioTrack Settings", None, "location")

        try:
            res = biotrackthc_call(action, data)
        except BioTrackClientError as ex:
            frappe.local.message_log.pop()
            frappe.throw(ex.message, title="Error")  # response nicer error message

        # sync derivatives
        items = []
        if res.get("derivatives"):
            defaukt_warehouse = get_default_warehouse()

            try:
                for derivative in res.get("derivatives"):
                    item_group = frappe.get_doc("Item Group", {"external_id": derivative.get("barcode_type")})
                    qty = flt(amount_map[cint(derivative.get("barcode_type"))])

                    item = make_item(barcode=derivative.get("barcode_id"), properties={
                        "item_group": item_group.name,
                        "default_warehouse": defaukt_warehouse.name,
                        "strain": self.strain,
                        "stock_uom": "Gram",
                        "is_stock_item": 1,
                        "actual_qty": qty,
                        "plant": self.name,
                    }, qty=qty)

                    items.append(item.item_code)
            except Exception as ex:
                self.harvest_cure_undo({}, action, res.get("transactionid"))
                raise

        if self.state == "Growing":
            self.state = "Drying"

        # Remove from Cultivation
        if self.dry_weight == self.wet_weight or (action == "plant_cure" and not additional_collection):
            self.disabled = 1

        self.transaction_id = res.get("transactionid")
        self.save()

        return {"items": items, "action": action, "transaction_id": res.get("transactionid")}

    @Document.whitelist
    def harvest_cure_undo(self, items, action, transaction_id):
        action += "_undo"
        res = biotrackthc_call(action, {'transactionid': transaction_id})

        # cleanup items
        if items:
            for barcode in items:
                item = frappe.get_doc("Item", {"barcode": barcode})
                entries = frappe.get_list("Stock Entry", {"item_code": item.item_code})
                for name in entries:
                    entry = frappe.get_doc("Stock Entry", name)
                    entry.cancel()
                    entry.delete()
                item.delete()

        if action == "plant_harvest":
            self.state = "Growing"

        if action == "plant_cure" and self.disabled:
            self.disabled = 0

        self.transaction_id = res.get("transactionid")
        self.save()

    @Document.whitelist
    def destroy_schedule(self, reason, reason_txt=None, override=None):
        data = {
            'barcodeid': [self.name],
            'reason_extended': removal_reasons.keys()[removal_reasons.values().index(reason)],
            'reason': reason_txt
        }

        if self.remove_scheduled and not override:
            frappe.throw(
                "Plant <strong>{}</strong> has already been scheduled for destruction. Check <strong>`Reset Scheduled time`</strong> to override.".format(
                    self.name))

        if override:
            data['override'] = 1

        biotrackthc_call("plant_destroy_schedule", data)

        self.remove_scheduled = 1
        self.remove_reason = reason_txt or reason
        self.remove_time = now()
        self.save()

    @Document.whitelist
    def destroy_schedule_undo(self):
        biotrackthc_call("plant_destroy_schedule_undo", {'barcodeid': [self.name]})
        self.remove_scheduled = 0
        self.remove_reason = None
        self.remove_time = None
        self.save()

    @Document.whitelist
    def harvest_schedule(self):
        biotrackthc_call("plant_harvest_schedule", {'barcodeid': [self.name]})
        self.harvest_scheduled = 1
        self.harvest_schedule_time = now()
        self.save()

    @Document.whitelist
    def harvest_schedule_undo(self):
        if self.state == "Drying":
            frappe.throw("Plant <strong>{}</strong> was already on harvesting process.".format(self.name))

        biotrackthc_call("plant_harvest_schedule_undo", {'barcodeid': [self.name]})
        self.harvest_scheduled = 0
        self.harvest_schedule_time = None
        self.save()

    @Document.whitelist
    def move_to_inventory(self):
        items = [self.name]
        res = biotrackthc_call("plant_convert_to_inventory", {'barcodeid': [self.name]})
        defaukt_warehouse = get_default_warehouse()
        item_group = frappe.get_doc("Item Group", {"external_id": 12})  # Mature Plant
        qty = 1

        for barcode in items:
            make_item(barcode=barcode, properties={
                "item_group": item_group.name,
                "default_warehouse": defaukt_warehouse.name,
                "strain": self.strain,
                "is_stock_item": 1,
                "actual_qty": qty,
                "plant": self.name,
                "parent_item": self.source,
            }, qty=qty)

        # destroy plant as well
        self.remove_scheduled = 1
        self.disabled = 1
        self.transaction_id = res.get("transactionid")
        self.save()

    @Document.whitelist
    def destroy(self):
        biotrackthc_call("plant_destroy", {'barcodeid': [self.name]})
        self.delete()


@frappe.whitelist()
def harvest_cure_undo(name, items, action, transaction_id):
    """Alias to harvest_cure_undo method to avoid check_if_latest exception"""
    plant = frappe.get_doc("Plant", name)

    import json
    try:
        items = json.loads(items)
    except ValueError:
        items = []

    return plant.harvest_cure_undo(items, action, transaction_id)


def get_plant_list(doctype, txt, searchfield, start, page_len, filters):
    fields = ["name", "strain"]
    match_conditions = build_match_conditions("Plant")
    match_conditions = "and {}".format(match_conditions) if match_conditions else ""

    return frappe.db.sql("""select %s from `tabPlant` where docstatus < 2
		and (%s like %s or strain like %s)
		{match_conditions}
		order by
		case when name like %s then 0 else 1 end,
		case when strain like %s then 0 else 1 end,
		name, strain limit %s, %s""".format(match_conditions=match_conditions) %
                         (", ".join(fields), searchfield, "%s", "%s", "%s", "%s", "%s", "%s"),
                         ("%%%s%%" % txt, "%%%s%%" % txt, "%%%s%%" % txt, "%%%s%%" % txt, start, page_len))


def bulk_clone(name):
    source_plant = frappe.get_doc("Plant", name)

    if source_plant.qty > 1:
        warehouse = frappe.get_doc("Warehouse", source_plant.get("warehouse"))
        location = frappe.get_value("BioTrack Settings", None, "location")
        remaining_qty = source_plant.qty - 1

        result = biotrackthc_call("plant_new", {
            "room": warehouse.external_id,
            "quantity": remaining_qty,
            "strain": source_plant.strain,
            "source": source_plant.source,
            "mother": cint(source_plant.get("is_mother")),
            "location": location
        })

        for barcode in result.get("barcode_id"):
            plant = frappe.new_doc("Plant")
            plant.update({
                "barcode": barcode,
                "item_group": source_plant.item_group,
                "source": source_plant.source,
                "strain": source_plant.strain,
                "warehouse": source_plant.warehouse,
                "state": source_plant.state,
                "birthdate": now(),
            })

            plant.save()

        # save directly with sql to avoid mistimestamp check
        frappe.db.set_value("Plant", source_plant.name, "qty", 1, update_modified=False)
        frappe.publish_realtime("list_update", {"doctype": "Plant"})


def destroy_scheduled_plants():
    """Destroy expired Plants"""
    date = add_to_date(now(), days=-3)
    for name in frappe.get_list("Plant",
                                [["disabled", "=", 0], ["remove_scheduled", "=", 1], ["remove_time", "<", date]]):
        plant = frappe.get_doc("Plant", name)
        plant.disabled = 1
        plant.save()
