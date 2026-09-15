var mychart;


chiron.conceptViewWindow.refreshData = function() {
	var conceptId = chiron.state.currentConceptId;
	var entryId = chiron.state.currentEntryId;
	var prefilterValue = chiron.state.prefilterValue;
	var show_data_for_all_subjects = true;
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
	        //         console.log(progressResponse);
	        //
	        //     }
	        // }
		})
		.done(function( response ) {
		    json = JSON.parse(response);
            //console.log(json);

            $('#chiron-count-missing-values').html(chiron.manager.integerFormat(json.count_missing_values));
			$('#chiron-count-subjects-with-missing-values').html(chiron.manager.integerFormat(json.count_subjects_with_missing_values));
			$('#chiron-null-and-missing-stats').show();

            if ( json.hasOwnProperty('histogram_data') ) {
			    if (!mychart) {
                    conceptHistogram.series[0].data = json.histogram_data;
                    mychart = Highcharts.chart('chiron-histogram-div', conceptHistogram);
                    chiron.state.highcharts = [];
                    chiron.state.highcharts.push(mychart);
                } else {
                    mychart.series[0].update({
                        name: 'Entries',
                        data: json.histogram_data
                    }, true);
                }
            }

            if ( json.hasOwnProperty('stats') ) {
                var statString = '<span class="badge badge-secondary ml-5">ENTRIES</span> '
                statString += '<strong>' + json.stats.count_non_null + '</strong>'
                statString += '<span class="badge badge-secondary ml-5">UNIQUE PATIENTS</span> '
                statString += '<strong>' + json.stats.unique_patients + '</strong>'
                statString += '<span class="badge badge-secondary ml-5">MIN</span> '
                statString += '<strong>' + json.stats.min + '</strong>'
                statString += '<span class="badge badge-secondary ml-5">MAX</span> '
                statString += '<strong>' + json.stats.max + '</strong>'


                $('#chiron-concept-stats-div').html(statString);
                $('input[name="cd_numeric_min"]').attr("placeholder", json.stats.min);
                $('input[name="cd_numeric_max"]').attr("placeholder", json.stats.max);
            }

            chiron.conceptViewWindow.attachEvents();

			$('#chiron-data-still-streaming').html("");
		})
		.fail(chiron.state.handle_ajax_fail);
	}
}



conceptHistogram = {
    chart: {
        type: 'column'
    },
    title: {
        text: ''
    },
    subtitle: {
        text: ''
    },
    credits: {
        enabled: false
    },
    xAxis: {
        type: 'category',
        labels: {
            style: {
                fontSize: '13px',
                fontFamily: 'Verdana, sans-serif'
            }
        },
        title: {
            text: 'Value'
        }
    },
    yAxis: {
        min: 0,
        title: {
            text: 'Entry count'
        }
    },
    legend: {
        enabled: false
    },
    series: [{
        name: 'Entries',
        data: []
    }]
}

$(document).ready(function() {
	$('.chiron-date-form-tab').click(function() {
		var queryType = $(this).attr('data-query-type');
		$('#chiron-date-form-query-type').val(queryType);
	});
	$( ".datepicker" ).unbind().each(function() {
		var initialDate = $(this).attr('placeholder');
		if (initialDate) {
			$(this).datepicker({
				defaultViewDate: initialDate
			});
		} else {
			$(this).datepicker();
		}
	});
});



chiron.conceptViewWindow.refreshData();
