from django.template.loader import render_to_string


class CohortDefProcessorBuiltInUiMixin:
    """
    CohortDefProcessor functionality needed by the built-in UI. If you are only using the
    API, your processors don't need this mixin.

    Needed properties:
    - self.form_html_template
    - self.form_js_template (optional)
    """

    def generate_concept_form(self, oConcept, statistics, form_options):
        context = statistics
        context["form_options"] = form_options
        context["oConcept"] = oConcept
        response = {}
        response["html"] = render_to_string(self.form_html_template, context)
        if hasattr(self, "form_js_template") and self.form_js_template:
            response["js_code"] = render_to_string(self.form_js_template, context)
        return response
