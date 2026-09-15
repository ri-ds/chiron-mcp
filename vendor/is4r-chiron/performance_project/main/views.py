from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.core.management import call_command

from chiron.authorization import dataset_selector


@login_required
@dataset_selector
def reload_patient_data(request):
    print("run the etl")
    call_command("chiron_run_etl")
    return redirect("chiron:home")
