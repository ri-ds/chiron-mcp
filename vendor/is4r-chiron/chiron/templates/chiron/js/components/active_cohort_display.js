

chiron.activeCohortDisplay = {};

chiron.activeCohortDisplay.initialize = function() {
	chiron.activeCohortDisplay.attachEvents();
	chiron.activeCohortDisplay.refresh();
}

chiron.activeCohortDisplay.refresh = function() {
	$('#active-cohort-def-div').addClass('disabled-section');
	$.ajax({
		type: "GET",
		headers: {          
		    Accept: "text/plain; charset=utf-8" 
		},
		url: "{% url 'chiron:api:cohort_def-list' %}"
	})
	.done(function( response ) {
		json = JSON.parse(response);
		$('#active-cohort-def-div').html(json.html);
		// modals go straight into body at the end
		$(document.body).append(json.modals);
		$('#describe-cohort-modal-body').html(json.describe);
		chiron.activeCohortDisplay.attachEvents();
		$('#active-cohort-def-div').removeClass('disabled-section');
	})
	.fail(chiron.state.handle_ajax_fail);
}

chiron.activeCohortDisplay.attachEvents = function() {
	$('.chiron-toggle-add-container-tool').click(function(e) {
		e.preventDefault();
		$('#chiron-add-container-tool').toggleClass("invisible");
	});
	$('.chiron-cohort-def-undo-redo').click(function() {
		var snapshotId = $(this).attr('data-snapshot-id');
		if (snapshotId) {
			$.ajax({
				type: "GET",
				url: "{% url 'chiron:api:cohort_def-list' %}" + snapshotId,
				data: {
					set_to_active : true
				}
			})
			.done(function( json ) {
				chiron.manager.cohortDefChanged();
			})
			.fail(chiron.state.handle_ajax_fail);
		}
	});
	$('.chiron-cohort-def-clear').unbind().click(function() {
		$('#active-cohort-def-div').addClass('disabled-section');
		$.ajax({
			type: "POST",
			// dataType: "json",
			url: "{% url 'chiron:api:cohort_def-list' %}",
			data: JSON.stringify({
				transformation: {
					type: 'clear_all'
				}
			})
		})
		.done(function( json ) {
			chiron.manager.cohortDefChanged();
		})
		.fail(function(e) {
			console.log(e);
		});
	});
	$('.chiron-add-container').click(function() {
		var collectionId = $(this).attr('data-collection-id');
		$.ajax({
			type: "POST",
			url: "{% url 'chiron:api:cohort_def-list' %}",
			data: JSON.stringify({
				transformation: {
					type: 'add_criteria_set',
					collection_id: collectionId,
				}
			})
		})
		.done(function( json ) {
			chiron.manager.cohortDefChanged();
		})
		.fail(chiron.state.handle_ajax_fail);
	});
	$('.chiron-delete-cd-entry').unbind().click(function() {
		$('#active-cohort-def-div').addClass('disabled-section');
		var entryId = $(this).attr('data-entry-id');
		$.ajax({
			type: "POST",
			// dataType: "json",
			url: "{% url 'chiron:api:cohort_def-list' %}",
			data: JSON.stringify({
				transformation: {
					type: 'delete_entry',
					entry_id: entryId,
				}
			})
		})
		.done(function( json ) {
			chiron.manager.cohortDefChanged();
		})
		.fail(function(e) {
			console.log(e);
		});
	});
	$('.chiron-delete-cd-container').unbind().click(function() {
		$('#active-cohort-def-div').addClass('disabled-section');
		var entryId = $(this).attr('data-entry-id');
		$.ajax({
			type: "POST",
			url: "{% url 'chiron:api:cohort_def-list' %}",
			data: JSON.stringify({
				transformation: {
					type: 'delete_criteria_set',
					entry_id: entryId,
				}
			})
		})
		.done(function( json ) {
			chiron.manager.cohortDefChanged();
		})
		.fail(chiron.state.handle_ajax_fail);
	});
	$('.chiron-edit-cd-entry').unbind().click(function() {
		if (chiron.state.activeView != 'query_view') {
			chiron.state.activeView = 'query_view';
			chiron.manager.activeViewChanged();
		}
		var newConceptId =  $(this).attr('data-concept-id');
		var newEntryId =  $(this).attr('data-entry-id');
		var newPrefilterValue =  $(this).attr('data-prefilter-value');
		chiron.state.currentConceptId = newConceptId;
		chiron.state.currentEntryId = newEntryId;
		chiron.state.prefilterValue = newPrefilterValue;
		chiron.manager.currentConceptIdChanged();
	});
	$('.chiron-create-event-rule').unbind().click(function() {
		var entryId = $(this).attr('data-entry-id');
		$.ajax({
			type: "POST",
			url: "{% url 'chiron:api:cohort_def-list' %}",
			data: JSON.stringify({
				transformation: {
					type: 'create_event_rule',
					entry_id: entryId,
				}
			})
		})
		.done(function( json ) {
			chiron.manager.cohortDefChanged();
		})
		.fail(chiron.state.handle_ajax_fail);
	});
	$('.chiron-show-event-modal').unbind().click(function() {
		var entryId = $(this).attr('data-entry-id');
		var collectionId = $(this).attr('data-collection-id');
		chiron.manager.showEventModal(collectionId, entryId);
	});
	$('.chiron-show-criteria-set-modal').unbind().click(function() {
		var entryId = $(this).attr('data-entry-id');
		var collectionId = $(this).attr('data-collection-id');
		var tab = $(this).attr('data-tab');
		chiron.manager.showCriteriaSetModal(collectionId, entryId, tab);
	});
	$('.chiron-delete-event-rule').unbind().click(function() {
		var entryId = $(this).attr('data-entry-id');
		$.ajax({
			type: "POST",
			url: "{% url 'chiron:api:cohort_def-list' %}",
			data: JSON.stringify({
				transformation: {
					type: 'delete_event_rule',
					entry_id: entryId,
				}
			})
		})
		.done(function( json ) {
			chiron.manager.cohortDefChanged();
		})
		.fail(chiron.state.handle_ajax_fail);
	});
	
	// show/hide tools for a cd entry on hover
	$('.chiron-cd-entry').hover(function() {
		var id = $(this).attr('id');
		$('#' + id + ' .chiron-cd-entry-buttons').show();
		$('#' + id + ' .chiron-cd-entry-handle').show();
		$('#' + id + ' .chiron-cd-entry-relationship-tool').show();
		$('#' + id + ' .chiron-cd-entry-relationship-display').hide();
	}, function() {
		var id = $(this).attr('id');
		$('#' + id + ' .chiron-cd-entry-buttons').hide();
		$('#' + id + ' .chiron-cd-entry-handle').hide();
		$('#' + id + ' .chiron-cd-entry-relationship-tool').hide();
		$('#' + id + ' .chiron-cd-entry-relationship-display').show();
	});

	// show/hide alias edit button
	$('.chiron-criteria-set-name').hover(function() {
		var id = $(this).attr('id');
		$('#' + id + ' .chiron-criteria-set-name-buttons').show();
	}, function() {
		var id = $(this).attr('id');
		$('#' + id + ' .chiron-criteria-set-name-buttons').hide();
	});
	
	// show/hide tools for a criteria set on hover
	$('.chiron-criteria-set').hover(function() {
		var id = $(this).attr('id');
		$('#' + id + ' .chiron-criteria-set-buttons').show();
	}, function() {
		var id = $(this).attr('id');
		$('#' + id + ' .chiron-criteria-set-buttons').hide();
	});
	
	// show/hide tools for a date rule on hover
	$('.chiron-date-rule').hover(function() {
		var id = $(this).attr('id');
		$('#' + id + ' .chiron-date-rule-buttons').show();
	}, function() {
		var id = $(this).attr('id');
		$('#' + id + ' .chiron-date-rule-buttons').hide();
	});
	
	// allow cd entries to be resorted
	var sortableUpdateFunction = function( event, ui ) {		// triggers when dropped in a new place
		if (ui.sender == null) {								// prevents from being called twice
			var container = ui.item.parent();
			var entryId = container.attr('data-entry-id');
			var childIds = [];
			container.children().each(function(i) {
				var id = $(this).attr('data-entry-id');
				if (id) {
					childIds.push(id);
				}
			});
			$.ajax({
				type: "POST",
				url: "{% url 'chiron:api:cohort_def-list' %}",
				data: JSON.stringify({
					transformation: {
						type: 'sort_cd_entries',
						entry_id: entryId, 
						child_ids: childIds
					}
				})
			})
			.done(function( json ) {
				chiron.manager.cohortDefChanged();
			})
			.fail(chiron.state.handle_ajax_fail);
		}
	};
//	$('.chiron-cd-entry-group-root-collection').sortable({
//		connectWith: '.chiron-cd-entry-group-subcollection',
//		handle: ".chiron-cd-entry-handle",
//		update: sortableUpdateFunction
//	});
	$('.chiron-cd-entry-group-root-collection').sortable({
		handle: ".chiron-cd-entry-handle",
		update: sortableUpdateFunction
	});
	$('.chiron-cd-entry-group-subcollection').sortable({
		connectWith: '.chiron-cd-entry-group-subcollection',
		handle: ".chiron-cd-entry-handle",
		update: sortableUpdateFunction
	});
	$('#sortable').disableSelection();
	
	$('.chiron-change-to-boolean-or').unbind().click(function() {
		var entryId = $(this).attr('data-entry-id');
		console.log(entryId);
		$.ajax({
			type: "POST",
			url: "{% url 'chiron:api:cohort_def-list' %}",
			data: JSON.stringify({
				transformation: {
					type: 'change_to_boolean_or',
					entry_id: entryId,
				}
			})
		})
		.done(function( json ) {
			chiron.manager.cohortDefChanged();
		})
		.fail(chiron.state.handle_ajax_fail);
	});
	
	$('.chiron-change-to-boolean-and').unbind().click(function() {
		var entryId = $(this).attr('data-entry-id');
		console.log(entryId);
		$.ajax({
			type: "POST",
			url: "{% url 'chiron:api:cohort_def-list' %}",
			data: JSON.stringify({
				transformation: {
					type: 'change_to_boolean_and',
					entry_id: entryId,
				}
			})
		})
		.done(function( json ) {
			chiron.manager.cohortDefChanged();
		})
		.fail(chiron.state.handle_ajax_fail);
	});
	
	
	
	
	
	
}

//chiron.active



























