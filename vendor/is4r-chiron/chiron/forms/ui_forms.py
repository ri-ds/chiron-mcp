from django import forms

from chiron import models


class ReportForm(forms.ModelForm):
    project_other = forms.CharField(label="New project name", required=False)

    class Meta:
        model = models.UserCreatedContent
        fields = [
            "dataset",
            "name",
            "project",
            "project_other",
            "description",
            "public",
            "share_with",
        ]
        labels = {
            "public": "Public (share with everyone)",
        }
        # TODO: what should this be set to?
        empty_labels = {
            "project": "not set",
        }
        widgets = {
            "share_with": forms.CheckboxSelectMultiple,
            "dataset": forms.HiddenInput,
            # "project": SelectWithAutocreate,
        }

    def __init__(self, chironuser, *args, **kwargs):
        super(ReportForm, self).__init__(*args, **kwargs)
        self.fields["project"].empty_label = "--- create new ---"
        self.fields["project"].queryset = models.Project.objects.accessible(
            dataset=chironuser.dataset
        )
        # exclude sharing with owner
        qChironUser = models.ChironUser.objects.exclude(id=chironuser.id)
        # only share with ChironUsers associated with this dataset
        qChironUser = qChironUser.filter(dataset=chironuser.dataset)
        # exclude chiron users who only have aggregated access
        qChironUser = qChironUser.exclude(access_level=models.ChironUser.AccessLevel.AGG)
        self.fields["share_with"].queryset = qChironUser

    def clean(self):
        data = self.cleaned_data
        has_error = False
        # verify only sharing with allowed people
        for oChironUser in data.get("share_with", []):
            if oChironUser.access_level == oChironUser.AccessLevel.AGG:
                self.add_error(
                    "share_with", f"user {oChironUser} doesn't have permission to view reports"
                )
                has_error = True
            oDataset = data["dataset"]
            if oChironUser.dataset != oDataset:
                self.add_error(
                    "share_with", f"user {oChironUser} is not associated with dataset {oDataset}"
                )
                has_error = True
        # create new project if needed
        if not data["project"] and data["project_other"] and not has_error:
            oProject = models.Project(name=data["project_other"], dataset=data["dataset"])
            oProject.save()
            data["project"] = oProject
        return data

    def save_m2m2(self):
        """
        Save_m2m() doesn't work when an intermediary table is defined on a M2M relationship
        This will mimic that
        """
        # erase any existing m2m relationships
        qCS = models.ContentSharing.objects.filter(content=self.instance)
        qCS.delete()

        # save new m2m relationships
        qChironUser = self.cleaned_data["share_with"]
        for oChironUser in qChironUser:
            oCS = models.ContentSharing(
                content=self.instance,
                chironuser=oChironUser,
            )
            oCS.save()


class ReportSharingForm(forms.ModelForm):
    class Meta:
        model = models.UserCreatedContent
        fields = ["share_with"]
        widgets = {
            "share_with": forms.CheckboxSelectMultiple,
        }
        labels = {
            "share_with": "Other users with access to this report:",
        }

    def __init__(self, chironuser, *args, **kwargs):
        super(ReportSharingForm, self).__init__(*args, **kwargs)
        # exclude sharing with owner
        qChironUser = models.ChironUser.objects.exclude(id=chironuser.id)
        # only share with ChironUsers associated with this dataset
        qChironUser = qChironUser.filter(dataset=chironuser.dataset)
        # exclude chiron users who only have aggregated access
        qChironUser = qChironUser.exclude(access_level=models.ChironUser.AccessLevel.AGG)
        self.fields["share_with"].queryset = qChironUser

    def clean(self):
        data = self.cleaned_data
        # verify only sharing with allowed people
        for oChironUser in data.get("share_with", []):
            if oChironUser.access_level == oChironUser.AccessLevel.AGG:
                self.add_error(
                    "share_with", f"user {oChironUser} doesn't have permission to view reports"
                )
            oDataset = self.instance.dataset
            if oChironUser.dataset != oDataset:
                self.add_error(
                    "share_with", f"user {oChironUser} is not associated with dataset {oDataset}"
                )
        return data
