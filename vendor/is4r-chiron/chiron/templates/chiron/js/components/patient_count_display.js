chiron.patientCountDisplay = {};

chiron.patientCountDisplay.initialize = function() {
	chiron.patientCountDisplay.refresh()
}

chiron.patientCountDisplay.refresh = function() {
	$('.active-cohort-count').html('<i class="fas fa-sync fa-spin"></i>');
	if(chiron.patientCountDisplay.hasOwnProperty("xhr") && chiron.patientCountDisplay.xhr.readyState != 4){
		chiron.patientCountDisplay.xhr.abort();
    }
	chiron.patientCountDisplay.xhr = $.ajax({
		url: "{% url 'chiron:api:query_tools-list' %}count",
	})
	.done(function( json ) {
		console.log(json);
		$('.active-cohort-count').html(json.count);
	})
	.fail(chiron.state.handle_ajax_fail);
}