from django.http import JsonResponse
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required


@login_required
def ajax_view_mode_widget(request):
    """
    HTML for the widget to choose show data for all patients or just active cohort
    """
    context = {}
    context["data_view_mode"] = request.session.get("data_view_mode", "all")
    response = {"data_view_mode": context["data_view_mode"]}
    response["html"] = render_to_string(
        "chiron/snippets/data_view_mode_widget.html", context, request=request
    )
    return JsonResponse(response)


@login_required
def ajax_set_data_view_mode(request):
    """
    Change view mode for django session (all patients or active cohort only)
    """
    data_view_mode = request.GET.get("data_view_mode")
    if data_view_mode not in ["active", "all"]:
        return JsonResponse("invalid data_view_mode", status=400, safe=False)
    request.session["data_view_mode"] = data_view_mode
    context = {
        "data_view_mode": data_view_mode,
    }
    response = {
        "html": render_to_string(
            "chiron/snippets/data_view_mode_widget.html", context, request=request
        ),
        "data_view_mode": data_view_mode,
    }
    return JsonResponse(response)
