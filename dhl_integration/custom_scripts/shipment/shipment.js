frappe.ui.form.on('Shipment', {
	refresh: function(frm){
		if (frm.doc.docstatus === 1 && !frm.doc.shipment_id) {
			frm.add_custom_button(__('Create DHL Shipment'), function() {
				frappe.call({
					"method": "dhl_integration.custom_scripts.shipment.shipment.create_shipment",
					"args": {
						"shipment": frm.doc.name
					},
					"freeze": true,
					"callback": function(ret){
						frappe.msgprint("Shipment created successfully");
						frm.reload_doc();
					}
				});
			});
		}
	},
	
	fetch_shipping_rates: function(frm){
		frappe.msgprint("It's here alright");
	}
});
