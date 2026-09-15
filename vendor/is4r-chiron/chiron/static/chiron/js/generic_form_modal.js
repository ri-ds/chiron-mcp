

var genericModal = {};



function executeFunctionByName(functionName, context /*, args */) {
	var args = Array.prototype.slice.call(arguments, 2);
	var namespaces = functionName.split(".");
	var func = namespaces.pop();
	for(var i = 0; i < namespaces.length; i++) {
		context = context[namespaces[i]];
	}
	return context[func].apply(context, args);
}

genericModal.attachFormModalEvents = function() {

	$('#id_project').on('change', function() {
  		console.log( this.value );
  		if (this.value == '') {
  			$('#div_id_project_other').show();
		} else {
  			$('#div_id_project_other').hide();
		}
	});

	$('#id_project').trigger('change');

	$('.ajax-form').submit(function(e) {
		e.preventDefault();
		$('.ajax-form-button').attr("disabled", true);
		var url = $(this).attr('data-url');
		//var data = $(this).serialize();
		var formData = new FormData(this);  //needed to handle file uploads
		$.ajax({
		  url: url,
		  type: "POST",
		  data: formData,
		  processData: false,		// needed to handle file uploads
		  contentType: false,		// needed to handle file uploads
		})
		.done(function( json ) {
		  if (json.status == 'complete') {
			  // this line prevents a reload of a POST request
			// window.location.href = window.location.href;
			if (json.hasOwnProperty('redirect')) {
				window.location.href = json.redirect;
			} else if (json.hasOwnProperty('onSuccess')) {
				executeFunctionByName(json.onSuccess, window);
			} else {
				location.reload();
			}
		  } else {
			  $('#generic-form-modal-title').html(json.title);
			  $('#generic-form-modal-body').html(json.html);
			  genericModal.attachFormModalEvents();
		  }
		})
		.fail(function( xhr, status, errorThrown ) {
		  alert( "error" );
		  console.log( "Error: " + errorThrown );
		  console.log( "Status: " + status );
		  console.dir( xhr );
		});
	});
}

genericModal.setOpenFormModalFunctionality = function() {
	$('.open-form-modal').unbind().click(function(e) {		
		  e.preventDefault();
		  e.stopPropagation();					// allows only button event even if button inside another clickable area
	      var url = $(this).attr('data-url');
	      $('#generic-form-modal-title').html('Loading...');
	      $('#generic-form-modal-body').html('');
	      $('#generic-form-modal').modal('show');
	      $.ajax({
	          url: url,
	          type: "GET",
	          dataType : "json",
	      })
	      .done(function( json ) {
	          $('#generic-form-modal-title').html(json.title);
	          $('#generic-form-modal-body').html(json.html);
	          if (json.hasOwnProperty('onLoad')) {
	        	  executeFunctionByName(json.onLoad, window);
	          }
	          genericModal.attachFormModalEvents();
	          //this gets reset in case there are any links to other form modals on this form
	          genericModal.setOpenFormModalFunctionality();
	      })
	      .fail(function( xhr, status, errorThrown ) {
	          alert( "error" );
	          console.log( "Error: " + errorThrown );
	          console.log( "Status: " + status );
	          console.dir( xhr );
	      });
	  });  
}

$(document).ready(function() {
  
	genericModal.setOpenFormModalFunctionality();
  
});


//customization of specific event modal forms
//this should perhaps be part of chiron object, but I only load
//the chiron object when working in the workspace, and some forms
//are accessible outside of the workspace.

attachReportFormEvents = function() {
	$('#id_public').change(function(){
     if (this.checked)
         $('#div_id_share_with').slideUp();
     else
         $('#div_id_share_with').slideDown();
 	 });
	$('#id_public').trigger( "change" );

	$("#chiron-show-edit-report-tab").click(function(e) {
		e.preventDefault();
		$("#chiron-edit-report-selector-div").show();
		$("#chiron-report-form-div").html('');
		$("#chiron-show-create-report-tab").removeClass("active");
		$(this).addClass("active");
	})

	$('#chiron-select-report-to-overwrite').change(function() {
		var reportId = $(this).val();
		$('#chiron-report-form-div').html("");
		if (reportId) {
			var url = $('option:selected', this).attr("data-url");
			$.ajax({
				  url: url,
				  type: "GET",
				  dataType : "json",
				  data: {overwrite_query_def_with_active: true}
			})
			.done(function( json ) {
				$('#chiron-report-form-div').html(json.html);
				if (json.hasOwnProperty('onLoad')) {
				  executeFunctionByName(json.onLoad, window);
				}
				genericModal.attachFormModalEvents();
				//this gets reset in case there are any links to other form modals on this form
				genericModal.setOpenFormModalFunctionality();
			})
			.fail(function( xhr, status, errorThrown ) {
				  alert( "error" );
				  console.log( "Error: " + errorThrown );
				  console.log( "Status: " + status );
				  console.dir( xhr );
			});
		}
	});

}

