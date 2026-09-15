

chiron.addIdFieldModal = {};


chiron.addIdFieldModal.initialize = function() {
	
}

chiron.addIdFieldModal.show = function() {
	$.ajax({
		type: "GET",
		url: "{% url 'chiron:ajax_get_add_id_field_form' %}",
	})
	.done(function( json ) {
		$('#chiron-add-id-field-modal-body').html(json.html);
		chiron.addIdFieldModal.attachEvents();
		$('#chiron-add-id-field-modal').modal('show');
	})
	.fail(chiron.state.handleAjaxFail);
	

	
}

chiron.addIdFieldModal.addAllFields = function(newFieldData) {
	// iterate ajax calls 1 at a time, then refresh table view
	if (newFieldData.length > 0) {
		var transformation = newFieldData.pop()
		transformation.type = 'add_entry';
        $.ajax({
            type: 'POST',
            url: "{% url 'chiron:api:table_def-list' %}",
            data: JSON.stringify({
            	transformation: transformation,
            })
        })
        .done(function( json ) {
        	chiron.addIdFieldModal.addAllFields(newFieldData);
        })
        .fail(chiron.state.handleAjaxFail);;
    } else {
    	chiron.manager.tableDefChanged();
    	$('#chiron-add-id-field-modal').modal('hide');
    }
}

chiron.addIdFieldModal.attachEvents = function() {
	$(".chiron-add-id-field").unbind().click(function() {
		
		var newFields = [];
		$('input:checked', $("#chiron-add-id-field-table")).each(function() {
			newFields.push({
				concept_id : $(this).attr('data-concept-id'),
				position : "prepend",
				aggregation_method : $(this).attr('data-aggregation-method'),
			});
		});
		chiron.addIdFieldModal.addAllFields(newFields);
	});
}