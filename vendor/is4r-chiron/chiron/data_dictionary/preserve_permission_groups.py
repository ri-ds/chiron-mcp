from chiron import models


class PreservePermissionGroups:
    """
    When restoring a dataset, permission groups are deleted and recreated - which breaks the
    FK references from ChironUser to permission groups. This tool can save the references to
    memory and then attempt to restore them after the dataset is restored.

    This feature should always be used inside a database transaction.
    """

    def __init__(self):
        self.errors = []
        self.backup = {}
        self.permission_groups_backed_up = False

    def backup_to_memory(self, oDataset=None):
        qChironUser = models.ChironUser.objects.all()
        if oDataset:
            qChironUser = qChironUser.filter(dataset=oDataset)
        for oChironUser in qChironUser:
            for oGroup in oChironUser.permission_groups.all():
                if oChironUser.pk not in self.backup:
                    self.backup[oChironUser.pk] = []
                self.backup[oChironUser.pk].append(oGroup.name)
        self.permission_groups_backed_up = True

    def permission_groups_found(self):
        if not self.permission_groups_backed_up:
            raise Exception("You must first run backup_to_memory().")
        if not self.backup:
            return False
        return True

    def restore_to_database(self):
        for chiron_user_id in self.backup:
            oChironUser = models.ChironUser.objects.get(pk=chiron_user_id)
            for group_name in self.backup[chiron_user_id]:
                oGroup = models.PermissionGroup.objects.filter(name=group_name).first()
                if oGroup:
                    oChironUser.permission_groups.add(oGroup)
                else:
                    msg = "Couldn't restore permission group '{}' for user '{}'".format(
                        group_name, oChironUser
                    )
                    print(msg)
                    self.errors.append(msg)
