import frappe
from dhl_integration.dhl_integration.doctype.dhl_settings.dhl_settings import DHLUtils

@frappe.whitelist()
def create_shipment(shipment):
	dhl = DHLUtils()
	return dhl.create_shipment(shipment)
