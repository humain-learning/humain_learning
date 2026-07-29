frappe.pages["generate-qr"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "QR Generator",
		single_column: true,
	});

	const layout = $(`
		<div class="row">
			<div class="col-lg-7">
				<div id="form-container"></div>
			</div>

			<div class="col-lg-5 text-center">
				<div id="qr-result"></div>
			</div>
		</div>
	`);

	page.body.append(layout);

	const fields = new frappe.ui.FieldGroup({
		body: $("#form-container"),
		fields: [
			{
				fieldtype: "Data",
				fieldname: "data",
				label: "Text or URL to encode",
				placeholder: "ABC123, https://example.com etc.",
				reqd: 1,
			},
			{
				fieldtype: "Select",
				fieldname: "type",
				label: "Data Type",
				options: "URL\nText",
				placeholder: "URL or Text",
			},
			{
				fieldtype: "Select",
				fieldname: "product",
				label: "Generating for",
				options: "Personal Use\nHumain Learning\nHAILM",
				placeholder: "Personal Use, Humain Learning, or HAILM",
			},
			{
				fieldtype: "Check",
				fieldname: "brand_colours",
				label: "Use Brand colours",
				default: 1,
				depends_on:
					"eval:doc.product == 'Humain Learning' || doc.product == 'HAILM'",
			},
			{
				fieldtype: "Check",
				fieldname: "brand_logo",
				label: "Use Brand Logo",
				default: 1,
				depends_on:
					"eval:doc.product == 'Humain Learning' || doc.product == 'HAILM'",
			},
		],
	});

	fields.make();

	const result = $("#qr-result");

	page.set_primary_action("Generate QR Code", () => {
		const values = fields.get_values();
		if (!values) return;

		const filename = `${values.data.substring(0, 30)}.png`
			.replace(/[<>:"/\\|?*]+/g, "_")
			.replace("https://", "")
			.replace("http://", "");

		frappe.call({
			method:
				"humain_learning.humain_learning.page.generate_qr.generate_qr.generate_qr_code",
			args: {
				values,
			},
			freeze: true,
			freeze_message: "Generating QR Code...",
			callback(r) {
				if (!r.message) return;

				result.html(`
					<img
						src="${r.message.image}"
						style="max-width: 400px; width: 100%; border: 1px solid #ccc;"
					>

					<div class="mt-4">
						<a
							href="${r.message.image}"
							download="${filename}"
							class="btn btn-primary"
						>
							Download
						</a>
					</div>
				`);
			},
		});
	});
};