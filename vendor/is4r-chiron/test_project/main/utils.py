from chiron.models import PermissionGroup, Dataset
from django.contrib.auth import get_user_model


def setup_default_chironuser_permission_groups():
    """
    Default chironusers for datasets "dataset1_stored" and "dataset2_stored" are stored in
    `test_project/test_project.json`. But the M2M relationships between the ChironUser and
    PermissionGroups are difficult to store in a fixture. Instead we run this code to get those
    relationships set up correctly.

    This should be run every time the `test_project/test_project.json` fixture is loaded. That
    happens in management command `restore_test_project_state` and at the start of each test in
    method `initialize_dd()`.
    """
    # add user permission groups
    oGroup = PermissionGroup.objects.get(name="all")
    User = get_user_model()
    oUser = User.objects.get(username="admin")
    oDataset = Dataset.objects.get(unique_id="dataset1_stored")
    for oChironUser in oUser.chironuser_set.filter(dataset=oDataset):
        oChironUser.permission_groups.add(oGroup)
    oUser = User.objects.get(username="agguser")
    for oChironUser in oUser.chironuser_set.filter(dataset=oDataset):
        oChironUser.permission_groups.add(oGroup)

    oGroup = PermissionGroup.objects.get(name="married")
    oUser = User.objects.get(username="demouser")
    for oChironUser in oUser.chironuser_set.filter(dataset=oDataset):
        oChironUser.permission_groups.add(oGroup)
