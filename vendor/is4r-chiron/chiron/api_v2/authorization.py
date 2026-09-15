from chiron import models
from chiron.authorization import get_request_chironuser
from django.core.exceptions import PermissionDenied


def set_chironuser_dataset(request, passed_args):
    if "dataset_string" in passed_args:
        unique_dataset_id = passed_args["dataset_string"]
        oDataset = models.Dataset.objects.get(unique_id=unique_dataset_id)
        request.chironuser = get_request_chironuser(request, oDataset)
        return request
    else:
        raise PermissionDenied


def url_dataset_check(oDataset, passed_args):
    if "dataset_string" in passed_args:
        if oDataset.unique_id != passed_args["dataset_string"]:
            raise PermissionDenied
