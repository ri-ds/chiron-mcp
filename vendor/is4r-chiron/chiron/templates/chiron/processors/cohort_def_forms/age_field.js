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
	        //
	        //     }
	        // }
		})
		.done(function( response ) {
		    json = JSON.parse(response);

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
                statString += '<span class="badge badge-secondary ml-5">AVG</span> '
                statString += '<strong>' + json.stats.avg_year + 'y, ' + json.stats.avg_day + 'd</strong>'
                +'</strong>'
                statString += '<span class="badge badge-secondary ml-5">MIN</span> '
                statString += '<strong>' + json.stats.min_year + 'y, ' + json.stats.min_day + 'd</strong>'
                statString += '<span class="badge badge-secondary ml-5">MAX</span> '
                statString += '<strong>' + json.stats.max_year + 'y, ' + json.stats.max_day + 'd</strong>'


                $('#chiron-concept-stats-div').html(statString);
                $('input[name="cd_age_min_year"]').attr("placeholder", json.stats.min_year);
                $('input[name="cd_age_min_day"]').attr("placeholder", json.stats.min_day);
                $('input[name="cd_age_max_year"]').attr("placeholder", json.stats.max_year);
                $('input[name="cd_age_max_day"]').attr("placeholder", json.stats.max_day);
            }

            chiron.conceptViewWindow.attachEvents();
			$('#chiron-data-still-streaming').html("");
		})
		.fail(chiron.state.handle_ajax_fail);
	}
}



// creating a global variable here, not a particularly elegant way to do this...
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
    plotOptions: {
        series: {
          pointPadding: 0,
          groupPadding: 0,
          borderWidth: 0.5,
          borderColor: 'rgba(255,255,255,0.5)'
        }
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

chiron.conceptViewWindow.refreshData();