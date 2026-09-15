from . import chiron_settings


# def get_setting(setting_name, default):
#     if hasattr(settings, setting_name):
#         return getattr(settings, setting_name)
#     return default


def chiron_globals(request):
    viewing_as_other_user = None
    if hasattr(request, "viewing_as_other_user"):
        viewing_as_other_user = request.viewing_as_other_user
    dataset = request.dataset if hasattr(request, "dataset") else None
    chironuser = request.chironuser if hasattr(request, "chironuser") else None
    context = {
        "CHIRON_LOGOUT_URL": chiron_settings.CHIRON_LOGOUT_URL,
        "CHIRON_SITE_TITLE": chiron_settings.CHIRON_SITE_TITLE,
        "CHIRON_FOOTER_TEMPLATE": chiron_settings.CHIRON_FOOTER_TEMPLATE,
        "CHIRON_EXTRA_NAVBAR_ITEMS": chiron_settings.CHIRON_EXTRA_NAVBAR_ITEMS,
        "CHIRON_INFOBAR": chiron_settings.CHIRON_INFOBAR,
        "CHIRON_INFOBAR_TYPE": chiron_settings.CHIRON_INFOBAR_TYPE,
        "CHIRON_SHOW_ANALYSIS_VIEW": chiron_settings.CHIRON_SHOW_ANALYSIS_VIEW,
        "viewing_as_other_user": viewing_as_other_user,
        "active_dataset": dataset,
        "active_chironuser": chironuser,
    }

    # apply dataset-specific overrides
    if dataset:
        if dataset.override_site_title:
            context["CHIRON_SITE_TITLE"] = dataset.override_site_title
        if dataset.override_footer_template:
            context["CHIRON_FOOTER_TEMPLATE"] = dataset.override_footer_template
        if dataset.override_infobar:
            context["CHIRON_INFOBAR"] = dataset.override_infobar
        if dataset.override_infobar_type:
            context["CHIRON_INFOBAR_TYPE"] = dataset.override_infobar_type

    return context
