chiron.viewModeSelector = {};

chiron.viewModeSelector.initialize = function() {
	chiron.viewModeSelector.refresh();
}

chiron.viewModeSelector.refresh = function() {
	if (chiron.state.activeView == 'results_view') {
		$('#data-view-mode-widget-div').hide();
	} else if (chiron.state.activeView == 'analysis_view') {
		$('#data-view-mode-widget-div').hide();
	} else {
		$('#data-view-mode-widget-div').show();
		$.ajax({
			url: "{% url 'chiron:ajax_view_mode_widget' %}"
		})
		.done(function( json ) {
			chiron.state.dataViewMode = json.data_view_mode;
			$('#data-view-mode-widget-div').html(json.html);
			chiron.viewModeSelector.attachEvents();

		})
		.fail(chiron.state.handle_ajax_fail);
	}

}

chiron.viewModeSelector.attachEvents = function() {
	// view mode is stored both in server session and in js state. This code will change
	// session and then state.
	$('.chiron-change-data-view-mode').unbind().click(function() {
		var isChecked = $(this).is(":checked");
		
		if (isChecked) {
			var dataViewMode = 'active';
		} else {
			var dataViewMode = 'all';
		}
		
		//var dataViewMode = $(this).attr('data-view-mode');

		$.ajax({
			url: "{% url 'chiron:ajax_set_data_view_mode' %}",
			data: {data_view_mode: dataViewMode}
		})
		.done(function( json ) {
			chiron.state.dataViewMode = json.data_view_mode;
			chiron.manager.viewModeChanged();
		})
		.fail(chiron.state.handle_ajax_fail);

	});
}