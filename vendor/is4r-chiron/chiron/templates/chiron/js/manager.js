
chiron.manager = {}

chiron.manager.initialize = function () {
	// set state.activeView

	const access_level = document.getElementById('access_level').value;

	var activeView = window.location.hash.substr(1)
	if (activeView) {
		if (access_level == 'agg') {
			activeView = 'analysis_view';
		}

		chiron.state.activeView = activeView;
	}

	// initialize widgets
	chiron.mainNavigator.initialize();
	chiron.conceptSelector.initialize();
	if (access_level != 'agg') {
		chiron.activeCohortDisplay.initialize();
		chiron.patientCountDisplay.refresh();
	}
	chiron.viewModeSelector.initialize();
	chiron.dataPreview.initialize();
	chiron.dataAnalysis.initialize();
	chiron.eventModal.initialize();
	chiron.tableDefSortModal.attachEvents();

	// setup sidebar functionality (sidebars aren't considered components)
	$("#chiron-hide-right-sidebar").click(function (e) {
		chiron.manager.hideRightSidebar();
		e.preventDefault();
	});

	$("#chiron-hide-left-sidebar").click(function (e) {
		chiron.manager.hideLeftSidebar();
		e.preventDefault();
	});

	$("#chiron-show-right-sidebar").click(function (e) {
		chiron.manager.showRightSidebar();
		e.preventDefault();
	});

	$("#chiron-show-left-sidebar").click(function (e) {
		chiron.manager.showLeftSidebar();
		e.preventDefault();
	});
}

chiron.manager.showEventModal = function (collectionId, entryId) {
	chiron.eventModal.show(collectionId, entryId);
}

chiron.manager.hideLeftSidebar = function () {
	$(".left-sidebar").hide();
	$("#left-sidebar-placeholder").show();
	$(".main-content").css("left", 0);
	if (chiron.state.rightSidebarVisible) {
		$(".main-content").css("width", "calc(100vw - 350px)");
	} else {
		$(".main-content").css("width", "100vw");
	}
	chiron.state.leftSidebarVisible = false;
	chiron.state.highcharts.forEach(function (value, index, array) {
		value.reflow();
	});
}

chiron.manager.showLeftSidebar = function () {
	$(".left-sidebar").show();
	$("#left-sidebar-placeholder").hide();
	$(".main-content").css("left", "250px");
	if (chiron.state.rightSidebarVisible) {
		$(".main-content").css("width", "calc(100vw - 600px)");
	} else {
		$(".main-content").css("width", "calc(100vw - 250px)");
	}
	chiron.state.leftSidebarVisible = true;
	chiron.state.highcharts.forEach(function (value, index, array) {
		value.reflow();
	});
}

// chiron.manager.eliminateRightSidebar = function() {
// 	$(".right-sidebar").hide();
// 	$("#right-sidebar-placeholder").hide();
// 	if (chiron.state.leftSidebarVisible) {
// 		$(".main-content").css("width", "calc(100vw - 250px)");
// 	} else {
// 		$(".main-content").css("width", "100vw");
// 	}
// 	chiron.state.rightSidebarVisible = false;
// 	chiron.state.highcharts.forEach(function(value, index, array) {
// 		value.reflow();
// 	});
// }

chiron.manager.hideRightSidebar = function () {
	$(".right-sidebar").hide();
	$("#right-sidebar-placeholder").show();
	if (chiron.state.leftSidebarVisible) {
		$(".main-content").css("width", "calc(100vw - 250px)");
	} else {
		$(".main-content").css("width", "100vw");
	}
	chiron.state.rightSidebarVisible = false;
	chiron.state.highcharts.forEach(function (value, index, array) {
		value.reflow();
	});
}

chiron.manager.showRightSidebar = function () {
	$(".right-sidebar").show();
	$("#right-sidebar-placeholder").hide();
	if (chiron.state.leftSidebarVisible) {
		$(".main-content").css("width", "calc(100vw - 600px)");
	} else {
		$(".main-content").css("width", "calc(100vw - 350px)");
	}
	chiron.state.rightSidebarVisible = true;
	chiron.state.highcharts.forEach(function (value, index, array) {
		value.reflow();
	});
}

chiron.manager.showCriteriaSetModal = function (collectionId, entryId, tab) {
	chiron.criteriaSetModal.show(collectionId, entryId);
	chiron.criteriaSetModal.tab = tab;
}

chiron.manager.activeCohortChanged = function () {
	$('#generic-form-modal').modal('hide');
}



chiron.manager.conceptSearchStringChanged = function () {
	if (chiron.state.conceptSearchString == '') {
		$('#cohort-def-concept-selector').show();
		$('#chiron-concept-search-results').hide();
	} else {
		$('#cohort-def-concept-selector').hide();
		$('#chiron-concept-search-results').show();
		chiron.conceptSelector.runSearch();
	}
}

chiron.manager.reportCreated = function () {
	$('#generic-form-modal').modal('hide');
	alert('Report saved. Go to the "Reports" section to view.');
}

chiron.manager.cohortDefChanged = function (optionalEntryId) {
	$('#generic-form-modal').modal('hide');
	//update main view
	if (chiron.state.activeView == 'results_view') {
		chiron.dataPreview.refresh();
	}
	if (chiron.state.activeView == 'analysis_view') {
		chiron.dataAnalysis.refresh();
	}
	if (chiron.state.activeView == 'query_view') {
		chiron.conceptViewWindow.refresh(optionalEntryId);
	} else {
		$('#cohort-def-output').removeClass('disabled-section');
	}
	//update active_cohort_display
	chiron.activeCohortDisplay.refresh();
	//update patient count display
	chiron.patientCountDisplay.refresh();
}

chiron.manager.cohortDefMightChange = function () {
	// disable concept view window, active cohort display
	$('#cohort-def-output').addClass('disabled-section');
	$('#active-cohort-def-div').addClass('disabled-section');
}

chiron.manager.cohortDefFailedToChange = function () {
	// enable concept view window, active cohort display
	$('#cohort-def-output').removeClass('disabled-section');
	$('#active-cohort-def-div').removeClass('disabled-section');

}

chiron.manager.currentConceptIdChanged = function () {
	if (chiron.state.activeView == 'query_view') {
		chiron.conceptViewWindow.refresh();
	}
	chiron.conceptSelector.refresh();
}

chiron.manager.activeViewChanged = function () {
	chiron.mainNavigator.refresh();
	chiron.conceptSelector.refresh();
	chiron.viewModeSelector.refresh();
	if (chiron.state.activeView == 'results_view') {
		chiron.dataPreview.refresh();
	}
	if (chiron.state.activeView == 'analysis_view') {
		chiron.dataAnalysis.refresh();
	}
	if (chiron.state.activeView == 'query_view' && chiron.state.dataViewMode == 'active') {
		chiron.conceptViewWindow.refresh();
	}
}

chiron.manager.viewModeChanged = function () {
	chiron.viewModeSelector.refresh();
	if (chiron.state.activeView == 'query_view') {
		chiron.conceptViewWindow.refresh();
	}
	if (chiron.state.activeView == 'analysis_view') {
		chiron.dataAnalysis.refresh();
	}
}


chiron.manager.tableDefChanged = function () {
	chiron.conceptSelector.refresh();
	if (chiron.state.activeView == 'results_view') {
		chiron.dataPreview.refresh();
	}
}

chiron.manager.analysisDefChanged = function () {
	chiron.conceptSelector.refresh();
	if (chiron.state.activeView == 'analysis_view') {
		chiron.dataAnalysis.refresh();
	}
}


chiron.manager.objectifyForm = function (formArray) {
	//serialize data function
	var returnArray = {};
	for (var i = 0; i < formArray.length; i++) {
		let nameEntry = formArray[i]['name']
		if (nameEntry.endsWith('[]')) {
			var fieldName = nameEntry.substring(0, nameEntry.length - 2);
			if (returnArray.hasOwnProperty(fieldName)) {
				returnArray[fieldName].push(formArray[i]['value']);
			} else {
				returnArray[fieldName] = [formArray[i]['value']];
			}
		} else {
			returnArray[nameEntry] = formArray[i]['value'];
		}
	}
	return returnArray;
}

chiron.manager.integerFormat = function (x) {
	if (typeof x !== 'undefined') {
		return x.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
	}
	return null;
}

