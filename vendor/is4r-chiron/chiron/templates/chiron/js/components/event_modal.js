

chiron.eventModal = {};


chiron.eventModal.initialize = function() {
	
}

chiron.eventModal.show = function(collectionId, entryId) {
	$.ajax({
		type: "GET",
		url: "{% url 'chiron:api:collections-list' %}" + collectionId,
		data: {
			include_criteria_set_event_options: true,
			criteria_set_entry_id: entryId
		},
		headers: {
			Accept: "text/plain; charset=utf-8"
		}
	})
	.done(function( response ) {
		json = JSON.parse(response);
		$('#chiron-event-modal-title').html(json.title);
		$('#chiron-event-modal-body').html(json.html);
		chiron.eventModal.attachEvents();
		$( "#chiron-select-destination-event" ).trigger( "change" );
		$('#chiron-event-modal').modal('show');
	})
	.fail(chiron.state.handleAjaxFail);
}


chiron.eventModal.attachEvents = function() {

	$('.chiron-event-date-form').unbind().submit(function(e) {
		e.preventDefault();
		var form = $(this);
		var transformation = chiron.manager.objectifyForm( form.serializeArray() )
		console.log(transformation);
		transformation.type = "modify_event_rule";
		$.ajax({
			type: "POST",
			url: "{% url 'chiron:api:cohort_def-list' %}",
			data: JSON.stringify({
				transformation: transformation
			})
		})
		.done(function( json ) {
			if (!json.transformation_successful) {
				var errorHtml = ""
				for (var i=0; i<json.transformation_errors.length; i++) {
					errorHtml = errorHtml + '<div class="alert alert-danger">'
						+ json.transformation_errors[i] + '</div>'
				}
				$('#chiron-event-form-errors-'+transformation.option_type).html(errorHtml)
				chiron.eventModal.attachEvents();
			} else {
				$('#chiron-event-modal').modal('hide');
				chiron.manager.cohortDefChanged();
			}
		})
		.fail(chiron.state.handle_ajax_fail);
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

	$('#chiron-select-destination-event').on('change', function (e) {
	    var optionSelected = $("option:selected", this);
	    var valueSelected = this.value;
	    $('.chiron-relative-event-input-set').hide()
	    $('#chiron-relative-event-input-set-'+valueSelected).show()
	});
}




