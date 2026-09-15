

var textCallbackXhr;

var runTextFieldCallback = function(page) {
	$('#chiron-data-still-streaming').show();
	var searchString = $('#chiron-text-field-search-input').val();
	var prefilterValue = chiron.state.prefilterValue;
	var queryData = {
		search : searchString,
		page : page,
		prefilter_value: prefilterValue
	}
	if (chiron.state.dataViewMode == 'all') {
		queryData.show_all_data = true;
	}
	if (conceptId != null) {
		// cancel previous requests
		if (chiron.conceptViewWindow.hasOwnProperty("dataXhr") && chiron.conceptViewWindow.dataXhr.readyState != 4) {
			chiron.conceptViewWindow.dataXhr.abort();
		}
		var lastResponseLength = false;
		chiron.conceptViewWindow.dataXhr = $.ajax({
			url: "{% url 'chiron:api:concepts-list' %}" + conceptId + "/cohort_def_callback/",
			type: "GET",
			data: queryData,
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
	        //         console.log(progressResponse);
	        //
	        //     }
	        // }
		})
		.done(function( response ) {
		    json = JSON.parse(response);

		    $('#chiron-count-missing-values').html(chiron.manager.integerFormat(json.count_missing_values));
			$('#chiron-count-subjects-with-missing-values').html(chiron.manager.integerFormat(json.count_subjects_with_missing_values));
			$('#chiron-null-and-missing-stats').show();

            //console.log(json);
			$('#chiron-text-field-count').html(json.count);
			$('#chiron-text-field-paginated-results').html(json.html);
			textFieldAttachEvents();
			$('#chiron-data-still-streaming').hide();

		})
		.fail(chiron.state.handle_ajax_fail);
	}






	// if(textCallbackXhr && textCallbackXhr.readyState != 4){
	// 	textCallbackXhr.abort();
    // }
	// textCallbackXhr = $.ajax({
	// 	url: "{% url 'chiron:api:concepts-detail' oConcept.permanent_id %}",
	// 	data: queryData,
	// 	headers: {
	// 		Accept: "text/plain; charset=utf-8"
	// 	},
	// })
	// .done(function( response ) {
	// 	json = JSON.parse(response);
	// 	$('#chiron-text-field-count').html(json.count);
	// 	$('#chiron-text-field-paginated-results').html(json.html);
	// 	textFieldAttachEvents();
	// })
	// .fail(chiron.state.handle_ajax_fail);
}


var textFieldAttachEvents = function() {
	$('.chiron-text-field-run-callback').unbind().click(function() {
		var page = $(this).data('page');
		console.log(page);
		if (page) {
			runTextFieldCallback(page);
		}
	});
	
	$('.chiron-text-field-add-value').unbind().click(function() {
		var vals = $('#chiron-text-field-selection').val();
		var new_val = $(this).data('string');
		if (vals) {
			vals  = vals + '\n' + new_val;
		} else {
			vals  = new_val;
		}
		$('#chiron-text-field-selection').val(vals);
	});
}

//var textFieldDeactivate = function() {
//	$('.chiron-text-field-add-value').each(function() {
//		
//	});
//}



$('#chiron-text-field-search').click(function() {
	runTextFieldCallback(1);
	
});

$(window).keydown(function(event){
    if(event.keyCode == 13) {
    	if ( $("#chiron-text-field-search-input").is(":focus") ) {
    		event.preventDefault();
            runTextFieldCallback(1);
            return false;
		}
        return True
    }
});

runTextFieldCallback(1);

