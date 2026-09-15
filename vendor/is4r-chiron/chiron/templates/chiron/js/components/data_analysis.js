

chiron.dataAnalysis = {};

chiron.dataAnalysis.initialize = function() {
	$("#analysis_data_preview").html('<div style="text-align:center;width:100%;padding-top:300px;"><i class="fas fa-2x fa-sync fa-spin"></i></div>');
	if (chiron.state.activeView == "analysis_view") {
		chiron.dataAnalysis.refresh();
	}
}

chiron.dataAnalysis.refresh = function(page) {
	$("#analysis_data_preview").addClass("disabled-section");
	chiron.dataPreview.metadataRequest = $.ajax({
		url: "{% url 'chiron:api:analysis_def-list' %}",
		data: {},
		headers: {
		    Accept: "text/plain; charset=utf-8"
		}
	})
	.done(function( response ) {
		json = JSON.parse(response);
		$('#analysis_data_preview').html(json.html);
		chiron.dataAnalysis.attachEvents();
		chiron.dataAnalysis.refreshData();
		$("#analysis_data_preview").removeClass("disabled-section");
	})
	.fail(chiron.state.handle_ajax_fail);
}

chiron.dataAnalysis.refreshData = function() {
	$("#chiron-analysis-loading-screen").show();
	// cancel previous requests
	if(chiron.dataAnalysis.hasOwnProperty("dataRequest") && chiron.dataAnalysis.dataRequest.readyState != 4){
		chiron.dataAnalysis.dataRequest.abort();
    }
	chiron.dataAnalysis.dataRequest = $.ajax({
		url: "{% url 'chiron:api:analysis_tools-list' %}run_analysis/",
		data: {},		// could set data view mode here, but for now always using active cohort
		headers: {
		    Accept: "text/plain; charset=utf-8"
		}
	})
	.done(function( response ) {
		json = JSON.parse(response);
		$('#chiron-analysis-output').html(json.html);
		$("#chiron-analysis-loading-screen").hide();
	})
	.fail(chiron.state.handle_ajax_fail);
}

chiron.dataAnalysis.resort = function( event, ui ) {
	if (ui.sender == null) {								// prevents from being called twice
		if (ui.sender == null) {								// prevents from being called twice
			var container = ui.item.parent();
			var role = container.attr('data-role');
			var entryId = ui.item.attr('data-entry-id');
			indexPosition = null;
			container.children().each(function(i) {
				if ($(this).attr('data-entry-id') == entryId) {
					indexPosition = i;
					return false;	// breaks the each loop
				}
			});
			$.ajax({
				type: "POST",
				url: "{% url 'chiron:api:analysis_def-list' %}",
				processData: false,
				data: JSON.stringify({
					transformation: {
						type: "move_entry",
						entry_id: entryId,
						role:  role,
						index: indexPosition
					}
				})
			})
			.done(function( json ) {
				chiron.manager.analysisDefChanged();
			})
			.fail(chiron.state.handleAjaxFail);
		}
	}
};

chiron.dataAnalysis.attachEvents = function() {

	// need to modify the export csv link based on current data view mode
	var adlink = $('#export-analysis-def-csv-link').attr("href");
	// for now, we always use the active cohort in the built-in ui
	$('#export-analysis-def-csv-link').attr("href", adlink + '?use_active_cohort=true');
	// if (chiron.state.dataViewMode == 'all') {
	// 	$('#export-analysis-def-csv-link').attr("href", adlink + '?use_active_cohort=false');
	// } else {
	// 	$('#export-analysis-def-csv-link').attr("href", adlink + '?use_active_cohort=true');
	// }

	$("#chiron-analysis-swap-rows-and-cols").unbind().click(function(e) {
		e.preventDefault();
		$.ajax({
			type: "POST",
			url: "{% url 'chiron:api:analysis_def-list' %}",
			processData: false,
			data: JSON.stringify({
				transformation: {
					type: "swap_rows_and_cols",
				}
			})
		})
		.done(function( json ) {
			chiron.manager.analysisDefChanged();
		})
		.fail(chiron.state.handleAjaxFail);
	});
	$(".chiron-clear-all-ad-fields").unbind().click(function(e) {
		e.preventDefault();
		$.ajax({
			type: "POST",
			url: "{% url 'chiron:api:analysis_def-list' %}",
			processData: false,
			data: JSON.stringify({
				transformation: {
					type: "clear_all",
				}
			})
		})
		.done(function( json ) {
			chiron.manager.analysisDefChanged();
		})
		.fail(chiron.state.handleAjaxFail);
	});
	$(".chiron-delete-analysis-entry").unbind().click(function(e) {
		e.preventDefault();
		var entryId = $(this).attr('data-entry-id');
		$.ajax({
			type: "POST",
			url: "{% url 'chiron:api:analysis_def-list' %}",
			processData: false,
			data: JSON.stringify({
				transformation: {
					type: "delete_entry",
					entry_id: entryId
				}
			})
		})
		.done(function( json ) {
			chiron.manager.analysisDefChanged();
		})
		.fail(chiron.state.handleAjaxFail);
	});
	$('#chiron-analysis-rows').sortable({
		connectWith: '#chiron-analysis-cols',
		update: chiron.dataAnalysis.resort
	});
	$('#chiron-analysis-cols').sortable({
		connectWith: '#chiron-analysis-rows',
		update: chiron.dataAnalysis.resort
	});
}