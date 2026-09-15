
chiron.dataPreview = {};


chiron.dataPreview.initialize = function() {
	$("#export_data_preview").html('<div style="text-align:center;width:100%;padding-top:300px;"><i class="fas fa-2x fa-sync fa-spin"></i></div>');
	if (chiron.state.activeView == "results_view") {
		chiron.dataPreview.refresh();
	}
}

chiron.dataPreview.refresh = function(page) {
	$("#export_data_preview").addClass("disabled-section");
	if (!page) {
		var page = 1;
	}
	// cancel previous requests
	if(chiron.dataPreview.hasOwnProperty("metadataRequest") && chiron.dataPreview.metadataRequest.readyState != 4){
		chiron.dataPreview.metadataRequest.abort();
    }
	chiron.dataPreview.metadataRequest = $.ajax({
		url: "{% url 'chiron:api:query_tools-list' %}preview_metadata/",
		data: {page: page},
		headers: {          
		    Accept: "text/plain; charset=utf-8" 
		}
	})
	.done(function( response ) {
		json = JSON.parse(response);
		$('#export_data_preview').html(json.html);
		chiron.dataPreview.attachEvents();
		genericModal.setOpenFormModalFunctionality();
		//chiron.dataPreview.refreshData(1);
		$("#chiron-preview-show-report-btn").show();
		$("#export_data_preview").removeClass("disabled-section");
	})
	.fail(chiron.state.handle_ajax_fail);
}



chiron.dataPreview.refreshData = function(page) {
	$("#chiron-preview-paginator-div").addClass("disabled-section");
	$("#chiron-preview-show-report-btn").hide();
	$("#chiron-preview-loading-screen").show();
	// cancel previous requests
	if(chiron.dataPreview.hasOwnProperty("dataRequest") && chiron.dataPreview.dataRequest.readyState != 4){
		chiron.dataPreview.dataRequest.abort();
    }
	chiron.dataPreview.dataRequest = $.ajax({
		url: "{% url 'chiron:api:query_tools-list' %}preview/",
		data: {page: page, output_type: "html"},
		headers: {          
		    Accept: "text/plain; charset=utf-8" 
		}
	})
	.done(function( response ) {
		json = JSON.parse(response);
		$('#chiron-preview-metadata').html(json.metadata);
		$('#chiron-preview-paginator-div').html(json.paginator);
		$('#chiron-preview-tbody').html(json.dataset);
		chiron.dataPreview.attachEvents();
		genericModal.setOpenFormModalFunctionality();
		$("#chiron-preview-paginator-div").removeClass("disabled-section");
		$("#chiron-preview-loading-screen").hide();
	})
	.fail(chiron.state.handle_ajax_fail);
}

chiron.dataPreview.attachTdEntryFormEvents = function() {
	$('.chiron-table-def-entry-form').unbind().submit(function(e) {
		e.preventDefault();
		var transformation = chiron.manager.objectifyForm( $(this).serializeArray() )
		transformation.type = 'add_entry'
		$.ajax({
			type: "POST",
			url: "{% url 'chiron:api:table_def-list' %}",
			data: JSON.stringify({
				transformation: transformation
			})
		})
		.done(function( json ) {
			$('#chiron-edit-td-entry-modal').modal('hide');
			chiron.manager.tableDefChanged();
		})
		.fail(chiron.state.handle_ajax_fail);
	});
	$('.form-check-input').change(function() {
		$('.chiron-aggregation-additional-inputs').hide();
		$('#chiron-aggregation-additional-inputs-'+this.value).slideDown();
	});
	$('.chiron-select-example').unbind().select2({
		minimumInputLength: 1,
		ajax: {
			//url: '/api/concepts/lab_description/cohort_def_callback/',
			url: function(params) {
				return $(this).attr('data-callback-url');
			},
			dataType: 'json',
			delay: 1000,
			data: function (params) {
				var query = {
					search: params.term,
					show_all_data: true,
					records_per_page: 200,
					json_flavor: "select2"
				}
				return query;
			}
		}
	});
}



chiron.dataPreview.attachEvents = function() {
	$("#chiron-preview-show-report-btn").unbind().click(function() {
		chiron.dataPreview.refreshData(1);
	});

	$('.chiron-get-td-entry-form').unbind().click(function() {
		var entryId = $(this).attr('data-entry-id');
		var conceptId = $(this).attr('data-concept-id');
		$.ajax({
			type: "GET",
			url: "{% url 'chiron:api:concepts-list' %}" + conceptId + "/?include_table_def_options=true",
			data: {table_def_entry_id: entryId},
			headers: {
				Accept: "text/plain; charset=utf-8"
			}
		})
		.done(function( response ) {
			json = JSON.parse(response);
			$('#chiron-edit-td-entry-modal-title').html(json.title);
			$('#chiron-edit-td-entry-modal-body').html(json.html);
			chiron.dataPreview.attachTdEntryFormEvents();
			$('#chiron-edit-td-entry-modal').modal('show');
		})
		.fail(chiron.state.handleAjaxFail);
	});
	
	$('.chiron-get-td-resort-form').unbind().click(function() {
		chiron.tableDefSortModal.show();
	});
	
	$('.chiron-get-add-id-field-form').unbind().click(function(e) {
		e.preventDefault();
		chiron.addIdFieldModal.show();
	});
	$('.chiron-table-def-undo-redo').unbind().click(function(e) {
		e.preventDefault();
		console.log("undo/redo");
		var snapshotId = $(this).attr('data-snapshot-id');
		if (snapshotId) {
			$.ajax({
				type: "GET",
				url: "{% url 'chiron:api:table_def-list' %}" + snapshotId,
				data: {
					set_to_active : true
				}
			})
			.done(function( json ) {
				console.log("looks like we finished");
				chiron.manager.tableDefChanged();
			})
			.fail(chiron.state.handle_ajax_fail);
		}
	});
	
	$('.chiron-clear-all-td-fields').unbind().click(function(e) {
		e.preventDefault();
		transformation = {
			type : "resort_columns",
			entry_ids : []
		}
		$.ajax({
			type: "POST",
			url: "{% url 'chiron:api:table_def-list' %}",
			data: JSON.stringify({
				transformation: transformation
			})
		})
		.done(function( json ) {
			chiron.manager.tableDefChanged();
		})
		.fail(chiron.state.handleAjaxFail);
	});
	$('.chiron-duplicate-td-entry').unbind().click(function() {
		var entryId = $(this).attr('data-entry-id');
		$.ajax({
			type: "POST",
			url: "{% url 'chiron:api:table_def-list' %}",
			data: JSON.stringify({
				transformation: {
					type: 'duplicate_entry',
					entry_id: entryId,
				}
			})
		})
		.done(function( json ) {
			chiron.manager.tableDefChanged();
		})
		.fail(chiron.state.handleAjaxFail);
	});
	$('.chiron-delete-td-entry').unbind().click(function() {
		var entryId = $(this).attr('data-entry-id');
		$.ajax({
			type: "POST",
			url: "{% url 'chiron:api:table_def-list' %}",
			data: JSON.stringify({
				transformation: {
					type: 'delete_entry',
					entry_id: entryId,
				}
			})
		})
		.done(function( json ) {
			chiron.manager.tableDefChanged();
		})
		.fail(chiron.state.handleAjaxFail);
	});
	$('.chiron-change-sort-order').unbind().click(function(event) {
		event.preventDefault();
		var entryId = $(this).attr('data-entry-id');
		$.ajax({
			type: "POST",
			url: "{% url 'chiron:api:table_def-list' %}",
			data: JSON.stringify({
				transformation: {
					type: "add_sort_entry",
					entry_id: entryId
				}
			})
		})
		.done(function( json ) {
			chiron.manager.tableDefChanged();
		})
		.fail(chiron.state.handleAjaxFail);
	});
	$('.chiron-change-paginator-page').unbind().click(function(e) {
		e.preventDefault();
		var page = $(this).attr('data-page');
		chiron.dataPreview.refreshData(page);
	});
	
	// show/hide tools for a td entry on hover
	$('.chiron-td-entry').unbind().hover(function() {
		var id = $(this).attr('id');
		$('#' + id + ' .chiron-td-entry-buttons').show();
	}, function() {
		var id = $(this).attr('id');
		$('#' + id + ' .chiron-td-entry-buttons').hide();
	});
	


}

