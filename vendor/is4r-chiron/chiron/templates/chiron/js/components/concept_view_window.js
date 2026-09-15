
// This is the window where the concept form gets displayed


chiron.conceptViewWindow = {};


chiron.conceptViewWindow.refresh = function() {
	chiron.conceptViewWindow.loadCohortDefMenu(null);
}

chiron.conceptViewWindow.loadCohortDefMenu = function() {
	$('#cohort-def-output').addClass('disabled-section');
	var conceptId = chiron.state.currentConceptId;
	var entryId = chiron.state.currentEntryId;
	var show_data_for_all_subjects = true;
	var data = {
		//concept_id: conceptId,
		cohort_def_entry_id: entryId,
		include_cohort_def_options: true,
		prefilter_value: chiron.state.prefilterValue
	}
	if (chiron.state.dataViewMode == 'all') {
		data.show_all_data = true;
	}
	if (conceptId != null) {
		// cancel previous requests
		if (chiron.conceptViewWindow.hasOwnProperty("xhr") && chiron.conceptViewWindow.xhr.readyState != 4) {
			chiron.conceptViewWindow.xhr.abort();
		}
		chiron.conceptViewWindow.xhr = $.ajax({
			url: "{% url 'chiron:api:concepts-list' %}" + conceptId + "/",
			type: "GET",
			data: data,
			headers: {
				Accept: "text/plain; charset=utf-8"
			},
		})
			.done(function (response) {
				json = JSON.parse(response);
				$('#cohort-def-output').html(json.html);
				chiron.conceptViewWindow.attachEvents();
				if (json.hasOwnProperty('js_code')) {
					eval(json.js_code);
				}
				$('#cohort-def-output').removeClass('disabled-section');

			})
			.fail(chiron.state.handle_ajax_fail);
	}
}

chiron.conceptViewWindow.attachEvents = function() {
	$('.chiron-cohort-def-form').unbind().submit(function(e) {
		chiron.manager.cohortDefMightChange();
		e.preventDefault();
		var transformation = chiron.manager.objectifyForm( $(this).serializeArray() )
		transformation.type = "add_entry";
		transformation.prefilter_value = chiron.state.prefilterValue;
		transformation.ignore_warnings = true;
		$.ajax({
			type: "POST",
			url: "{% url 'chiron:api:cohort_def-list' %}",
			data: JSON.stringify({
				transformation: transformation
			})
		})
		.done(function( json ) {
			if (json.transformation_successful) {
				chiron.state.currentEntryId = json.entry_id;
				chiron.manager.cohortDefChanged(json.entry_id);
			} else {
				console.log(json);
				$('#chiron-concept-form-errors').html('');
				for (i = 0; i < json.transformation_errors.length; i++) {
					$('#chiron-concept-form-errors').append(
						'<div class="alert alert-danger">' + json.transformation_errors[i] + '</div>'
					);
				} 
				chiron.manager.cohortDefFailedToChange();
			}	
		})
		.fail(chiron.state.handle_ajax_fail);
	});
	$('#chiron-prefilter-selector').unbind().change(function() {
		chiron.state.prefilterValue = this.value;
		chiron.conceptViewWindow.loadCohortDefMenu();
	});
	$('#chiron-prefilter-lookup-btn').unbind().click(function() {
		$('#prefilter-lookup-modal-body').html('<i class="fa fa-spinner fa-pulse fa-3x fa-fw"></i>');
		$('#prefilter-lookup-modal').modal('show');
		var prefilterSearch = $('#chiron-prefilter-text-input').val();
		var conceptId = $(this).attr('data-concept-id');
		$.ajax({
			type: "GET",
			url: "{% url 'chiron:api:concepts-list' %}" + conceptId + "/cohort_def_callback/",
			data: {
				search: prefilterSearch,
				show_all_data: true,
				records_per_page: 200,
				//rapid_search: true
			}
		})
		.done(function( json ) {
			console.log(json);
			var outstr = '<div class="list-group">';
			for (i=0; i<json.paginated_results.length; i++) {
				var val = json.paginated_results[i].unique_values;
				outstr += '<a href="#" class="list-group-item list-group-item-action no-underline prefilter-option" data-value="' + val + '">';
				outstr += val;
				outstr += '</a>';
			}
			outstr += '</div>';
			$('#prefilter-lookup-modal-body').html(outstr);
			$('.prefilter-option').click(function(e) {
				e.preventDefault();
				chiron.state.prefilterValue = $(this).attr('data-value');
				chiron.conceptViewWindow.loadCohortDefMenu();
				$('#prefilter-lookup-modal').modal('hide');
			});
		})
		.fail(chiron.state.handle_ajax_fail);

	});
	// $('#chiron-prefilter-lookup-btn').unbind().click(function() {
	// 	var prefilterSearch = $('#chiron-prefilter-text-input').val();
	// 	chiron.state.prefilterValue = $('#chiron-prefilter-text-input').val();
	// 	console.log(chiron.state.prefilterValue);
	// 	chiron.conceptViewWindow.loadCohortDefMenu();
	// });
}