from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string

from chiron.authorization import dataset_selector
from chiron import query_definition as qdef
from chiron import models


@login_required
@dataset_selector
def ajax_get_td_resort_form(request):
    table = qdef.Table(request.chironuser)
    context = {
        "extended_table_def": table.extended_table_def,
    }
    response = {}
    response["html"] = render_to_string(
        "chiron/table_def_display/td_resort_form.html",
        context,
        request=request,
    )
    return JsonResponse(response)


@login_required
@dataset_selector
def ajax_get_add_id_field_form(request):
    qCollection = models.Collection.objects.filter(event_id_field__isnull=False)
    context = {
        "qCollection": qCollection,
    }
    response = {}
    response["html"] = render_to_string(
        "chiron/table_def_display/add_id_field_form.html",
        context,
        request=request,
    )
    return JsonResponse(response)


# @login_required
# def ajax_get_td_entry_form(request):
#     entry_id = request.GET.get("entry_id")
#     table_def = qdef.clean_active_table_def(request)
#     td_entry = qdef.get_table_def_entry(table_def, entry_id)
#     oConcept = models.Concept.objects.get(permanent_id=td_entry["concept_id"])
#     display_processor = oConcept.get_display_processor(request.chironuser)
#     response = display_processor.get_table_form(td_entry)  # sets "html" and "js_code"
#     response[
#         "title"
#     ] = "How do you want to handle multiple values for <strong>{}?</strong>".format(
#       Concept.name
#     )
#     return JsonResponse(response)
