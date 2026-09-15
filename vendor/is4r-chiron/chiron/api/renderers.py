import json

from django.template.loader import render_to_string
from django.shortcuts import get_object_or_404

from rest_framework import renderers

from chiron import models


class CollectionTemplateRenderer(renderers.BaseRenderer):
    """
    Returns HTML snippet for built-in website
    """

    media_type = "text/plain"
    format = "json"
    charset = "utf-8"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        request = renderer_context["request"]
        # response = renderer_context['response']
        # template_name = response.template_name

        if request.query_params.get("include_criteria_set_options"):
            count_rule = data["criteria_set_options"][0]
            alias_rule = data["criteria_set_options"][1]
            context = data
            context["count_rule"] = count_rule
            context["alias_rule"] = alias_rule
            response = {}
            response["html"] = render_to_string(
                "chiron/cohort_def_display/criteria_set_form.html",
                context,
                request=request,
            )
            response["title"] = "Edit {} Criteria Set".format(data["name"].title())
        elif request.query_params.get("include_criteria_set_event_options"):
            context = data
            response = {}
            for option in data["criteria_set_event_options"]["event_options"]:
                option["criteria_set_entry_id"] = data["criteria_set_entry_id"]
                form_html = render_to_string(option["django_template"], option, request=request)
                option["form_html"] = form_html

            response["html"] = render_to_string(
                "chiron/cohort_def_display/event_date_form2.html",
                context,
                request=request,
            )
            response["title"] = "Event Rule for {} Collection".format(data["name"].title())
        return json.dumps(response)


class ConceptTemplateRenderer(renderers.BaseRenderer):
    """
    Returns HTML snippet for built-in website
    """

    media_type = "text/plain"
    format = "json"
    charset = "utf-8"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        request = renderer_context["request"]
        # response = renderer_context['response']
        # template_name = response.template_name

        if request.query_params.get("callback"):  # return cohort def form callback
            concept_id = data.get("permanent_id")
            oConcept = get_object_or_404(models.Concept, permanent_id=concept_id)
            data = data.get("callback_data", None)
            processor = oConcept.get_cohort_def_processor(request.chironuser)
            response = processor.generate_callback_html(oConcept, data)

        elif request.query_params.get("include_table_def_options"):  # return table_def form
            response = {}
            option_groups = {}
            option_selected = False
            for option in data["table_def_options"]["aggregation_options"]:
                if option["selected"]:
                    option_selected = True
                if option["group"] in option_groups:
                    option_groups[option["group"]].append(option)
                else:
                    option_groups[option["group"]] = [option]

            criteria_set_options = data["table_def_options"].get("criteria_set_options", [])
            entry_alias = data["table_def_options"].get("entry_alias", None)
            agg_criteria_set = data["table_def_options"]["selected_aggregation_criteria_set"]
            show_criteria_set_options = False
            if agg_criteria_set and agg_criteria_set not in criteria_set_options:
                show_criteria_set_options = True
            if len(criteria_set_options) > 1:
                show_criteria_set_options = True

            context = {
                "entry_id": data["table_def_options"].get("entry_id"),
                "criteria_set_options": criteria_set_options,
                "selected_aggregation_criteria_set": agg_criteria_set,
                "show_criteria_set_options": show_criteria_set_options,
                "concept_id": data.get("permanent_id"),
                "option_groups": option_groups,
                "option_selected": option_selected,
                "entry_alias": entry_alias,
                "collection_name": data["collection_name"],
                "collection_name_plural": data["collection_name_plural"],
            }
            response["html"] = render_to_string(
                "chiron/processors/table_def_forms/table_def_form.html",
                context,
                request=request,
            )
            t = "How do you want to handle multiple values for <strong>{}?</strong>".format(
                data["name"]
            )
            response["title"] = t

        elif request.query_params.get("include_cohort_def_options"):  # return cohort_def form
            concept_id = data.get("permanent_id")
            oConcept = get_object_or_404(models.Concept, permanent_id=concept_id)
            statistics = data.get("statistics", {})
            response = {"concept_id": oConcept.permanent_id}
            if "error" in statistics:
                error_classes = "chiron-concept-stat-error text-warning mt-5"
                form_body = '<div class="{}">{}</div>'.format(error_classes, statistics["error"])
            else:
                form_options = data.get("cohort_def_options", {})
                processor = oConcept.get_cohort_def_processor(request.chironuser)
                form_code = processor.generate_concept_form(oConcept, statistics, form_options)
                form_body = form_code["html"]
                if "js_code" in form_code and form_code["js_code"]:
                    response["js_code"] = form_code["js_code"]
            context = {
                "concept": data,
                "form_body": form_body,
                "concept_numeric_id": oConcept.id,  # used to create link for admin section
            }
            response["html"] = render_to_string(
                "chiron/snippets/cohort_def_form_container.html",
                context,
                request=request,
            )

        elif data.get("is_callback"):
            concept_id = data.get("permanent_id")
            oConcept = get_object_or_404(models.Concept, permanent_id=concept_id)
            processor = oConcept.get_cohort_def_processor(request.chironuser)
            response = data
            if hasattr(processor, "form_html_callback_template"):
                response["html"] = render_to_string(
                    processor.form_html_callback_template, data, request=request
                )
        else:  # return search results
            context = data
            context["search_string"] = request.query_params.get("search", None)
            response = {
                "html": render_to_string(
                    "chiron/snippets/concept_search_result.html", context, request=request
                ),
            }
        return json.dumps(response)


class CategoryTemplateRenderer(renderers.BaseRenderer):
    """
    Returns HTML snippet for built-in website
    """

    media_type = "text/plain"
    format = "json"
    charset = "utf-8"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        # view = renderer_context['view']
        request = renderer_context["request"]
        # response = renderer_context['response']
        # template_name = response.template_name
        context = {}
        context["categories"] = data.get("categories", [])
        context["concepts"] = data.get("concepts", [])
        context["category_id"] = data["category_id"]

        response = {
            "html": render_to_string(
                "chiron/snippets/concept_list.html", context, request=request
            ),
            "category_id": context["category_id"],
        }
        return json.dumps(response)


class CohortDefTemplateRenderer(renderers.BaseRenderer):
    """
    Returns HTML snippet for built-in website
    """

    media_type = "text/plain"
    format = "json"
    charset = "utf-8"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        request = renderer_context["request"]
        response = renderer_context["response"]
        template_name = response.template_name

        if response.status_code != 200:
            data = {}
            response.status_code = 200
        data["interactive"] = True
        data["qCollection"] = models.Collection.get_viewable_collections(
            request.chironuser
        ).order_by("name")
        response = {
            "html": render_to_string(template_name, data, request=request),
            "modals": render_to_string(
                "chiron/cohort_def_display/cohort_def_modals.html", data, request=request
            ),
            "describe": data.get("describe", ""),
        }
        return json.dumps(response)


class AnalysisDefTemplateRenderer(renderers.BaseRenderer):
    """
    Returns HTML snippet for built-in website
    """

    media_type = "text/plain"
    format = "json"
    charset = "utf-8"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        request = renderer_context["request"]
        response = renderer_context["response"]
        template_name = response.template_name

        if response.status_code != 200:
            data = {}
            response.status_code = 200
        response = {
            "html": render_to_string(template_name, data, request=request),
        }
        return json.dumps(response)


class AnalysisToolsTemplateRenderer(renderers.BaseRenderer):
    """
    Returns HTML snippet for built-in website
    """

    media_type = "text/plain"
    format = "json"
    charset = "utf-8"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        request = renderer_context["request"]
        response = renderer_context["response"]
        template_name = response.template_name

        if response.status_code != 200:
            data = {}
            response.status_code = 200

        response = {
            "html": render_to_string(template_name, data, request=request),
        }
        return json.dumps(response)


class QueryToolsTemplateRenderer(renderers.BaseRenderer):
    """
    Returns HTML snippet for built-in website
    """

    media_type = "text/plain"
    format = "json"
    charset = "utf-8"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        request = renderer_context["request"]
        response = renderer_context["response"]
        template_name = response.template_name

        if template_name:
            oTableDefSnapshot = models.TableDefSnapshot.get_active_snapshot(request.chironuser)
            if oTableDefSnapshot:
                data["previous_snapshot_id"] = oTableDefSnapshot.get_previous_id()
                data["next_snapshot_id"] = oTableDefSnapshot.get_next_id()
            else:
                data["previous_snapshot_id"] = None
                data["next_snapshot_id"] = None

            if "pipeline" in data:
                data["json_pipeline"] = json.dumps(data["pipeline"], indent=4)

            response = {
                "html": render_to_string(template_name, data, request=request),
            }
            return json.dumps(response)

        else:
            # need to insert empty columns if any aren't viewable due to permissions
            column_mask = []
            for td_entry in data["extended_table_def"]["fields"]:
                if td_entry["has_errors"]:
                    column_mask.append(False)
                else:
                    column_mask.append(True)
            if False in column_mask:
                modified_data = []
                if "data" in data:
                    for row in data["data"]:
                        modified_row = []
                        for has_data in column_mask:
                            if has_data:
                                modified_row.append(row.pop(0))
                            else:
                                modified_row.append("")
                        modified_data.append(modified_row)
                data["data"] = modified_data

            response = {
                "paginator": render_to_string(
                    "chiron/snippets/paginator_from_json.html", data, request=request
                ),
                "dataset": render_to_string(
                    "chiron/table_def_display/dataset.html", data, request=request
                ),
                "metadata": render_to_string(
                    "chiron/table_def_display/metadata.html", data, request=request
                ),
            }
            return json.dumps(response)


class ReportsTemplateRenderer(renderers.BaseRenderer):
    """
    Returns HTML snippet for built-in website
    """

    media_type = "text/plain"
    format = "json"
    charset = "utf-8"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        # view = renderer_context['view']
        request = renderer_context["request"]
        response = renderer_context["response"]
        # template_name = response.template_name
        context = response.data
        output = {
            "html": render_to_string(
                "chiron/reports/report_list.html",
                context,
                request=request,
            ),
        }
        return json.dumps(output)


class ReportToolsTemplateRenderer(renderers.BaseRenderer):
    """
    Returns HTML snippet for built-in website
    """

    media_type = "text/plain"
    format = "json"
    charset = "utf-8"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        # view = renderer_context['view']
        request = renderer_context["request"]
        response = renderer_context["response"]
        # template_name = response.template_name
        context = response.data
        context["custom_sort_string"] = ""
        sort_field = request.GET.get("sort_field", None)
        sort_direction = int(request.GET.get("sort_direction", 1))
        if sort_field:
            context["custom_sort_string"] = "&sort_field={}&sort_direction={}".format(
                sort_field, sort_direction
            )

        # we will show headers for columns with errors, but those columns won't be in the data.
        # So we have to rebuild the data skipping those columns
        column_mask = []
        for td_entry in context["extended_table_def"]["fields"]:
            if td_entry["has_errors"]:
                column_mask.append(False)
            else:
                column_mask.append(True)
        if False in column_mask:
            modified_data = []
            if "data" in context:
                for row in context["data"]:
                    modified_row = []
                    for has_data in column_mask:
                        if has_data:
                            modified_row.append(row.pop(0))
                        else:
                            modified_row.append("")
                    modified_data.append(modified_row)
            context["data"] = modified_data

        output = {
            "html": render_to_string(
                "chiron/reports/report_data_preview.html",
                context,
                request=request,
            ),
        }
        return json.dumps(output)
