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
						console.log(ret)
						if(ret.message == "OK"){
							frappe.msgprint("Shipment created successfully");
							frm.reload_doc();
						}
					}
				});
			});
		}
	}
});
