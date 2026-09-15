# from django.dispatch import receiver
# from django.db import models

# from .models import ChironUser, PermissionGroup


# @receiver(models.signals.post_save, sender=ChironUser)
# def add_default_permissions_to_new_chiron_user(sender, instance, created, **kwargs):
#     """This one saves if task is new task"""
#     if created:
#         qPerm = PermissionGroup.objects.filter(default_set_for_new_autocreated_users=True)
#         for oPerm in qPerm:
#             instance.permission_groups.add(oPerm)
