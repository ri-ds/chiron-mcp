

chiron.tableDefSortModal = {};


chiron.tableDefSortModal.initialize = function() {
	
}

chiron.tableDefSortModal.show = function() {
	$.ajax({
		type: "GET",
		url: "{% url 'chiron:ajax_get_td_resort_form' %}",
	})
	.done(function( json ) {
		$('#chiron-td-resort-modal-body').html(json.html);
		chiron.tableDefSortModal.attachEvents();
		$('#chiron-td-resort-modal').modal('show');
	})
	.fail(chiron.state.handleAjaxFail);
}

chiron.tableDefSortModal.attachEvents = function() {
	// sorting columns
	var sortableUpdateFunction2 = function( event, ui ) {		// triggers when dropped in a new place
		if (ui.sender == null) {								// prevents from being called twice
			console.log("dropped");
		}
	};
	
	$('#chiron-resort-modal-list').sortable({
		update: sortableUpdateFunction2
	});
	$('.chiron-change-td-sort-order').unbind().click(function() {
		var newSortOrder = []
		$("#chiron-resort-modal-list").children().each(function () {
			var entryId = $(this).attr("data-entry-id");
			newSortOrder.push(entryId);
		});
		transformation = {
			type : "resort_columns",
			entry_ids : newSortOrder
		}
		$.ajax({
			type: "POST",
			url: "{% url 'chiron:api:table_def-list' %}",
			data: JSON.stringify({
				transformation: transformation
			})
		})
		.done(function( json ) {
			chiron.manager.tableDefChanged();
			$('#chiron-td-resort-modal').modal('hide');
		})
		.fail(chiron.state.handleAjaxFail);
	});
}