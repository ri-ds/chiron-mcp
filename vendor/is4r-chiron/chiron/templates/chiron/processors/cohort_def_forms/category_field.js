chiron.conceptViewWindow.refreshData = function() {
	var conceptId = chiron.state.currentConceptId;
	var entryId = chiron.state.currentEntryId;
	var prefilterValue = chiron.state.prefilterValue;
	var data = {
		concept_id: conceptId,
		entry_id: entryId,
		prefilter_value: prefilterValue
	}
	if (chiron.state.dataViewMode == 'all') {
		data.show_all_data = true;
	}
	if (conceptId != null) {
		// cancel previous requests
		if(chiron.conceptViewWindow.hasOwnProperty("dataXhr") && chiron.conceptViewWindow.dataXhr.readyState != 4){
			chiron.conceptViewWindow.dataXhr.abort();
	    }
		var lastResponseLength = false;
		chiron.conceptViewWindow.dataXhr = $.ajax({
			url: "{% url 'chiron:api:concepts-list' %}" + conceptId + "/cohort_def_callback/",
			type: "GET",
			data: data,
			headers: {
				Accept: "text/plain; charset=utf-8"
			},
			// xhrFields: {
	        //     // Getting on progress streaming response
	        //     onprogress: function(e) {
			//
	        //     	var progressResponse;
	        //         var response = e.target.response;
	        //         if(lastResponseLength === false)
	        //         {
	        //             progressResponse = response;
	        //             lastResponseLength = response.length;
	        //         }
	        //         else
	        //         {
	        //             progressResponse = response.substring(lastResponseLength);
	        //             lastResponseLength = response.length;
	        //         }
	        //         // do something with partial response
	        //     }
	        // }
		})
		.done(function( response ) {
			json = JSON.parse(response);

			$('#chiron-count-missing-values').html(chiron.manager.integerFormat(json.count_missing_values));
			$('#chiron-count-subjects-with-missing-values').html(chiron.manager.integerFormat(json.count_subjects_with_missing_values));
			$('#chiron-null-and-missing-stats').show();

			// update the form
			if ( json.hasOwnProperty('values') ) {
				for (var i = 0; i < json.values.length; i++) {
					var entry = json.values[i];
					div_match = '.category-value-option-div[data-value="' + entry.category.replaceAll('"', '\\"') + '"]';
					$(div_match).attr("data-count", entry.count);
					$(div_match + ' .category-value-subject-count').html(chiron.manager.integerFormat(entry.uniquePatientCount));
					$(div_match + ' .category-value-entry-count').html(chiron.manager.integerFormat(entry.count));
					var barWidth = Math.round(entry.count / json.max_count * 100)
					$(div_match + ' .category-value-bar').width(barWidth + '%');
				}
			}
			chiron.conceptViewWindow.attachEvents();

			{% if not form_options.is_boolean_concept %}
			// resort everything correctly
			$('#category-list > div').sort(function(a,b) {
			    return parseInt($(a).attr("data-count")) < parseInt($(b).attr("data-count"));
			}).appendTo('#category-list');
			{% endif %}

			$('.category-value-count-description').show();

			$('#chiron-data-still-streaming').html("");
		})
		.fail(chiron.state.handle_ajax_fail);
	}
}

chiron.conceptViewWindow.refreshData();