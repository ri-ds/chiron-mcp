

chiron.mainNavigator = {}

chiron.mainNavigator.initialize = function() {
	chiron.mainNavigator.highlightActiveView();
	chiron.mainNavigator.attachEvents();
	chiron.mainNavigator.displayActiveView();
}

chiron.mainNavigator.refresh = function() {
	chiron.mainNavigator.highlightActiveView();
	chiron.mainNavigator.displayActiveView();
}

chiron.mainNavigator.attachEvents = function() {
	$('.chiron-view-selector').click(function(e) {
		// e.preventDefault();
		var view = $(this).attr('data-view');
		//chiron.state.loadView(view);
		chiron.state.activeView = view;
		chiron.manager.activeViewChanged();
	});
}

chiron.mainNavigator.displayActiveView = function() {
	// show or hide appropriate container
	//$('.main-content').hide();
	if (chiron.state.activeView == 'results_view') {
		$('#query-view-window').hide();
		$('#analysis-view-window').hide();
		$('#results-view-window').show();
	} else if (chiron.state.activeView == 'analysis_view') {
		$('#results-view-window').hide();
		$('#query-view-window').hide();
		$('#analysis-view-window').show();
	} else {	// query_view
		$('#results-view-window').hide();
		$('#analysis-view-window').hide();
		$('#query-view-window').show();
		// need to make sure all highcharts are sized appropriately for the space
		chiron.state.highcharts.forEach(function(value, index, array) {
			value.reflow();
		});
	}
}



chiron.mainNavigator.highlightActiveView = function() {
	$('.chiron-main-nav li').removeClass('active');
	$('.chiron-view-selector[data-view="' + chiron.state.activeView + '"]').parent().addClass('active');
}