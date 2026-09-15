chiron.conceptSelector = {};

chiron.conceptSelector.keypressEventsAttached = false;

chiron.conceptSelector.initialize = function() {
	$('#cohort-def-concept-selector').html('<div style="text-align:center;width:100%;"><i class="fas fa-sync fa-spin"></i></div>');
	$.ajax({
		url: "{% url 'chiron:api:concept_categories-list' %}",
		type: "GET",
		headers: {          
			Accept: "text/plain; charset=utf-8" 
		},
	})
	.done(function( response ) {
		json = JSON.parse(response);
		$('#cohort-def-concept-selector').html(json.html);
		chiron.conceptSelector.attachEvents();
		chiron.conceptSelector.refresh();
	})
	.fail(chiron.state.handle_ajax_fail);
}

chiron.conceptSelector.refresh = function() {
	chiron.conceptSelector.attachEvents();
	$('.chiron-concept-option').removeClass('chiron-selected-concept-option');
	if (chiron.state.activeView == 'query_view') {
		var conceptId = chiron.state.currentConceptId;
		$('.chiron-concept-option[data-concept-id="' + conceptId + '"]').addClass('chiron-selected-concept-option');
		$(".hide-in-results-view").css("display", "block");
		$(".hide-in-analysis-view").css("display", "block");
		$(".hide-in-query-view").css("display", "none");
		$('#chiron-search-results-count').html(chiron.state.resultCountCohortDef);
	}
	if (chiron.state.activeView == 'results_view') {
		$(".hide-in-query-view").css("display", "block");
		$(".hide-in-analysis-view").css("display", "block");
		$(".hide-in-results-view").css("display", "none");
		$('#chiron-search-results-count').html(chiron.state.resultCountTableDef);
		$.ajax({
			url: "{% url 'chiron:api:table_def-list' %}associated_concept_ids/"
		})
		.done(function( json ) {
			console.log(json);
			for (var i = 0; i < json.concept_ids.length; i++) { 
				$('.chiron-concept-option[data-concept-id="' + json.concept_ids[i] + '"]').addClass('chiron-selected-concept-option');
			}
		})
		.fail(chiron.state.handle_ajax_fail);
	}
	if (chiron.state.activeView == 'analysis_view') {
		$(".hide-in-query-view").css("display", "block");
		$(".hide-in-results-view").css("display", "block");
		$(".hide-in-analysis-view").css("display", "none");
		$('#chiron-search-results-count').html(chiron.state.resultCountTableDef);
		$.ajax({
			url: "{% url 'chiron:api:analysis_def-list' %}associated_concept_ids/"
		})
		.done(function( json ) {
			console.log(json);
			for (var i = 0; i < json.concept_ids.length; i++) {
				$('.chiron-concept-option[data-concept-id="' + json.concept_ids[i] + '"]').addClass('chiron-selected-concept-option');
			}
		})
		.fail(chiron.state.handle_ajax_fail);
	}
	
}


chiron.conceptSelector.attachEvents = function() {	
	$(".chiron-category-option[data-loaded='no']").unbind().click(function(e) {
		e.preventDefault();
		var categoryId = $(this).attr('data-category-id');
		$('#chiron-category-option-' + categoryId).after(
			'<div style="text-align:center;width:100%;" class="chiron-concept-selector-loading"><i class="fas fa-sync fa-spin"></i></div>'
		);
		$.ajax({
			type: "GET",
			url: "{% url 'chiron:api:concept_categories-list' %}" + categoryId,
			headers: {          
				Accept: "text/plain; charset=utf-8" 
			}
		})
		.done(function( response ) {
			json = JSON.parse(response);
			var categoryId = json.category_id;
			$('#chiron-category-option-' + categoryId).attr('data-loaded', 'yes');
			$('#chiron-category-option-' + categoryId).after(json.html);
			$('#chiron-category-display-indicator-' + categoryId).html('<i class="fas fa-angle-up"></i>');
			$('#chiron-category-option-' + categoryId).attr('data-displayed', 'yes');
			$('.chiron-concept-selector-loading').remove();
			chiron.conceptSelector.refresh();
		})
		.fail(chiron.state.handle_ajax_fail);
	});
	$(".chiron-category-option[data-loaded='yes']").unbind().click(function() {
		var categoryId = $(this).attr('data-category-id');
		var displayed = $('#chiron-category-option-' + categoryId).attr('data-displayed');
		if (displayed == 'yes') {
			$('#chiron-concept-container-' + categoryId).slideUp();
			$('#chiron-category-display-indicator-' + categoryId).html('<i class="fas fa-angle-down"></i>');
			$('#chiron-category-option-' + categoryId).attr('data-displayed', 'no');
		} else {
			$('#chiron-concept-container-' + categoryId).slideDown();
			$('#chiron-category-display-indicator-' + categoryId).html('<i class="fas fa-angle-up"></i>');
			$('#chiron-category-option-' + categoryId).attr('data-displayed', 'yes');
		}
	});
	
	if (chiron.state.activeView == 'results_view') {
		chiron.conceptSelector.attachResultsViewEvents();
	} else if (chiron.state.activeView == 'analysis_view') {
		chiron.conceptSelector.attachAnalysisViewEvents();
	} else{
		chiron.conceptSelector.attachQueryViewEvents();
	}
	
	$('#chiron-concept-search-btn').unbind().click(function() {
		var searchString = $('#chiron-concept-search-input').val();
		chiron.state.conceptSearchString = searchString.trim();
		chiron.manager.conceptSearchStringChanged();
	});	
	if (!chiron.conceptSelector.keypressEventsAttached) {
		$(document).on('keypress',function(e) {
		    if ( e.which == 13 && $("#chiron-concept-search-input").is(":focus") ) {
		    	$('#chiron-concept-search-btn').trigger( "click" );
		    }
		});
		chiron.conceptSelector.keypressEventsAttached = true;
	}
	$('.chiron-close-concept-search').unbind().click(function() {
		chiron.state.conceptSearchString = '';
		$('#chiron-concept-search-input').val('');
		chiron.manager.conceptSearchStringChanged();
	});
	
	
}

chiron.conceptSelector.attachResultsViewEvents = function() {
	$('.chiron-concept-option').unbind().click(function(e) {
		e.preventDefault();
		var conceptId = $(this).attr('data-concept-id');
		$.ajax({
			type: "POST",
			url: "{% url 'chiron:api:table_def-list' %}",
			processData: false,
			data: JSON.stringify({
				transformation: {
					type: "add_entry",
					concept_id: conceptId
				}
			})
		})
		.done(function( json ) {
			chiron.manager.tableDefChanged();
		})
		.fail(chiron.state.handleAjaxFail);
	});
}

chiron.conceptSelector.attachAnalysisViewEvents = function() {
	$('.chiron-concept-option').unbind().click(function(e) {
		e.preventDefault();
		var conceptId = $(this).attr('data-concept-id');
		$.ajax({
			type: "POST",
			url: "{% url 'chiron:api:analysis_def-list' %}",
			processData: false,
			data: JSON.stringify({
				transformation: {
					type: "add_entry",
					concept_id: conceptId
				}
			})
		})
		.done(function( json ) {
			chiron.manager.analysisDefChanged();
		})
		.fail(chiron.state.handleAjaxFail);
	});
}


chiron.conceptSelector.attachQueryViewEvents = function() {
	$('.chiron-concept-option').unbind().click(function(e) {
		e.preventDefault();
		var newConceptId =  $(this).attr('data-concept-id');
		chiron.state.currentConceptId = newConceptId;
		chiron.state.currentEntryId = null;
		chiron.state.prefilterValue = '';
		chiron.manager.currentConceptIdChanged();
	});
}


chiron.conceptSelector.runSearch = function() {
	$('#chiron-concept-search-results').html('<div style="text-align:center;width:100%;"><i class="fas fa-sync fa-spin"></i></div>');
	$.ajax({
		url: "{% url 'chiron:api:concepts-list' %}",
		headers: {          
			Accept: "text/plain; charset=utf-8" 
		},
		type: "GET",
		data: {search: chiron.state.conceptSearchString}
	})
	.done(function( response ) {
		json = JSON.parse(response);
		$('#chiron-concept-search-results').html(json.html);
		chiron.state.resultCountTotal = json.resultCountTotal;
		chiron.state.resultCountCohortDef = json.resultCountCohortDef;
		chiron.state.resultCountTableDef = json.resultCountTableDef;
//		if (chiron.state.activeView == 'query_view') {
//			$('#chiron-search-results-count').html(json.resultCountCohortDef);
//		} else {
//			$('#chiron-search-results-count').html(json.resultCountTableDef);
//		}
		
		chiron.conceptSelector.refresh();
	})
	.fail(chiron.state.handle_ajax_fail);
}

