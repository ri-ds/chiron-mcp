

chiron.criteriaSetModal = {};

chiron.criteriaSetModal.tab = null;		// used to set which tab to start as active

chiron.criteriaSetModal.initialize = function() {
	
}

chiron.criteriaSetModal.show = function(collectionId, entryId) {
	$.ajax({
		type: "GET",
		url: "{% url 'chiron:api:collections-list' %}" + collectionId + "/",
		data: {
			include_criteria_set_options: true,
			criteria_set_entry_id: entryId
		},
		headers: {
			Accept: "text/plain; charset=utf-8"
		}
	})
	.done(function( response ) {
		json = JSON.parse(response);
		$('#chiron-criteria-set-modal-title').html(json.title);
		$('#chiron-criteria-set-modal-body').html(json.html);
		if (chiron.criteriaSetModal.tab) {
			$('#' + chiron.criteriaSetModal.tab).click();
		}
		chiron.criteriaSetModal.attachEvents();
		$('#chiron-criteria-set-modal').modal('show');
	})
	.fail(chiron.state.handleAjaxFail);
}


chiron.criteriaSetModal.attachEvents = function() {
	$('.chiron-criteria-set-count-form').unbind().submit(function(e) {
		e.preventDefault();
		var transformation = chiron.manager.objectifyForm( $(this).serializeArray() )
		transformation.type = "add_criteria_set_count_rule"
		$.ajax({
			type: "POST",
			url: "{% url 'chiron:api:cohort_def-list' %}",
			data: JSON.stringify({
				transformation: transformation
			})
		})
		.done(function( json ) {
			$('#chiron-criteria-set-modal').modal('hide');
			chiron.manager.cohortDefChanged();
		})
		.fail(chiron.state.handle_ajax_fail);
	});
	$('.chiron-criteria-set-alias-form').unbind().submit(function(e) {
		e.preventDefault();
		var transformation = chiron.manager.objectifyForm( $(this).serializeArray() )
		transformation.type = "set_criteria_set_alias"
		$.ajax({
			type: "POST",
			url: "{% url 'chiron:api:cohort_def-list' %}",
			data: JSON.stringify({
				transformation: transformation
			})
		})
		.done(function( json ) {
			$('#chiron-criteria-set-modal').modal('hide');
			chiron.manager.cohortDefChanged();
		})
		.fail(chiron.state.handle_ajax_fail);
	});
}