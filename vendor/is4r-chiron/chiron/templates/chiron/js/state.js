// core objects
chiron = {};
chiron.state = {};

// initialize state
chiron.state.currentConceptId = null;
chiron.state.currentEntryId = null;

// if the current concept allows/requires prefiltering, set the concept to prefilter by and
// the value to use
// chiron.state.conceptForPrefilter = null;  // I don't think I need to track this
chiron.state.prefilterValue = '';


const access_level = document.getElementById('access_level').value;

if (access_level == 'agg') {
	chiron.state.activeView = 'analysis_view';
}
else {
	chiron.state.activeView = 'query_view';
}

chiron.state.dataViewMode = 'all';						// "all" or "active"
chiron.state.leftSidebarVisible = true;
chiron.state.rightSidebarVisible = true;

chiron.state.highcharts = [];							// store highcharts for triggering resize

// concept search values
chiron.state.conceptSearchString = '';
chiron.state.resultCountTotal = 0;
chiron.state.resultCountCohortDef = 0;
chiron.state.resultCountTableDef = 0;


// widgets

//chiron.projectTool = {};





// state ///////////////////////////////////////////////////////////////

//chiron.state.initialize = function() {
//	var activeView = window.location.hash.substr(1)
//	if (activeView) {
//		chiron.state.activeView = activeView;
//	}
//	
//	
//	chiron.state.loadView(chiron.state.activeView);
//	
//	chiron.mainNavigator.initialize();
//	chiron.conceptSelector.initialize();
//	chiron.activeCohortDisplay.attachEvents();
//	chiron.viewModeSelector.attachEvents();
//	chiron.patientCountDisplay.refresh();
//	
//	chiron.dataPreview.reload(1);
//	
//	
//}
//
//chiron.state.loadView = function(new_active_view) {
//	chiron.state.activeView = new_active_view;
//	chiron.mainNavigator.highlightActiveView();
//	$('.main-content').hide();
//	if (chiron.state.activeView == 'results_view') {
//		$('#results-view-window').show();
//	} else {
//		$('#query-view-window').show();
//	}
//	chiron.conceptSelector.attachEvents();
//}
//
//chiron.state.refreshResultsViewWindow = function() {
//	chiron.dataPreview.reload(1);
//}
//
//chiron.state.changeCurrentConceptId = function(new_concept_id) {
//	chiron.state.currentConceptId = new_concept_id;
//	chiron.conceptViewWindow.refresh();
//}
//
//chiron.state.activeCohortChanged = function(new_active_cohort_display_html) {
//	$('#active-cohort-def-div').html(new_active_cohort_display_html);
//	chiron.activeCohortDisplay.attachEvents();
//	chiron.patientCountDisplay.refresh();
//	if (chiron.state.dataViewMode == 'active') {
//		chiron.conceptViewWindow.refresh();
//	}
//}
//
//chiron.state.changeViewMode = function(new_view_mode) {
//	chiron.state.dataViewMode = new_view_mode;
//	chiron.conceptViewWindow.refresh();
//}

chiron.state.handleAjaxFail = function (xhr, status, errorThrown) {
	alert("error");
	console.log("Error: " + errorThrown);
	console.log("Status: " + status);
	console.dir(xhr);
}