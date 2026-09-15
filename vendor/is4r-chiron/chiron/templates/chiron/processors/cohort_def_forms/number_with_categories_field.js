var mychart;

chiron.conceptViewWindow.refreshData = function() {
	var conceptId = chiron.state.currentConceptId;
	var entryId = chiron.state.currentEntryId;
	var prefilterValue = chiron.state.prefilterValue;
	var show_data_for_all_subjects = true;
	var data = {
		concept_id: conceptId,
		entry_id: entryId,
		include_statistics: true,
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

		    console.log(json);
		    $('#chiron-count-missing-values').html(chiron.manager.integerFormat(json.count_missing_values));
			$('#chiron-count-subjects-with-missing-values').html(chiron.manager.integerFormat(json.count_subjects_with_missing_values));
			$('#chiron-null-and-missing-stats').show();

			if ( json.hasOwnProperty('histogram_data') ) {
			    if (!mychart) {
                    conceptHistogram.series[0].data = json.histogram_data;
                    mychart = Highcharts.chart('chiron-histogram-div', conceptHistogram);
                } else {
                    mychart.series[0].update({
                        name: 'Entries',
                        data: json.histogram_data
                    }, true);
                }
                //conceptHistogram.series[0].data = json.histogram_data;
                $('#chiron-histogram-div').show();
			    $('#chiron-histogram-div-empty').hide();
                Highcharts.chart('chiron-histogram-div', conceptHistogram);
            } else {
			    $('#chiron-histogram-div').hide();
			    $('#chiron-histogram-div-empty').show();
            }

			if ( json.hasOwnProperty('stats') ) {

                var statString = '<span class="badge badge-secondary ml-5">ENTRIES</span> '
                statString += '<strong>' + json.stats.count_non_null + '</strong>'
                statString += '<span class="badge badge-secondary ml-5">UNIQUE PATIENTS</span> '
                statString += '<strong>' + json.stats.unique_patients + '</strong>'
                statString += '<span class="badge badge-secondary ml-5">AVG</span> '
                statString += '<strong>' + json.stats.avg + '</strong>'
                statString += '<span class="badge badge-secondary ml-5">MIN</span> '
                statString += '<strong>' + json.stats.min + '</strong>'
                statString += '<span class="badge badge-secondary ml-5">MAX</span> '
                statString += '<strong>' + json.stats.max + '</strong>'


                $('#chiron-concept-stats-div').html(statString);
                $('input[name="cd_numeric_min"]').attr("placeholder", json.stats.min);
                $('input[name="cd_numeric_max"]').attr("placeholder", json.stats.max);
            }

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