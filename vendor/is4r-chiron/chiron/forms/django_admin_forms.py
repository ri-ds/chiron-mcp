from django import forms

from chiron import models


class ChironUserForm(forms.ModelForm):
    class Meta:
        model = models.ChironUser
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        oDataset = cleaned_data["dataset"]
        qPermissionGroup = cleaned_data["permission_groups"]
        for oPG in qPermissionGroup:
            if oPG.dataset != oDataset:
                msg = "Permission groups must be associated with the same dataset as this chiron user."  # noqa
                self.add_error("permission_groups", msg)
        return None


class CollectionForm(forms.ModelForm):
    class Meta:
        model = models.Collection
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        event_concept_fields = [
            "event_id_field",
            "event_name_field",
            "event_date_field",
            "event_end_date_field",
        ]
        for field_name in event_concept_fields:
            self._generic_clean_event_field(field_name, cleaned_data)
        return None

    def _generic_clean_event_field(self, field_name, cleaned_data):
        # you can't set this value during create, because the specified concept has to already
        # be associated with this collection
        oConcept = cleaned_data[field_name]
        if oConcept and not self.instance.pk:
            msg = (
                "You can't specify this field during collection creation. "
                "First create the collection, then create child concepts, then come "
                "back and edit the collection to specify which child concept to use here."
            )
            self.add_error(field_name, msg)
        # must choose a concept associated with this collection
        if oConcept and oConcept.collection != self.instance:
            self.add_error(
                field_name, "You must choose a concept associated with this collection."
            )


class CategoryForm(forms.ModelForm):
    class Meta:
        model = models.Category
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        oDataset = cleaned_data["dataset"]
        oParentCategory = cleaned_data["parent"]
        if oParentCategory and oParentCategory.dataset != oDataset:
            msg = "The category and parent category must be associated with the same dataset."
            self.add_error("parent", msg)
        return None


class SourceSourceDependencyForm(forms.ModelForm):
    class Meta:
        model = models.SourceSourceDependency
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        oSource = cleaned_data["source"]
        oDependency = cleaned_data["depends_on_source"]
        if oSource.collection.dataset != oDependency.collection.dataset:
            msg = "The depends_on_source must be associated with the same dataset."
            self.add_error("depends_on_source", msg)


class ConceptConceptDependencyForm(forms.ModelForm):
    class Meta:
        model = models.ConceptConceptDependency
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        oConcept = cleaned_data["concept"]
        oDependency = cleaned_data["depends_on_concept"]
        if oConcept.collection.dataset != oDependency.collection.dataset:
            msg = "The depends_on_concept must be associated with the same dataset."
            self.add_error("depends_on_concept", msg)


class ConceptSourceDependencyForm(forms.ModelForm):
    class Meta:
        model = models.ConceptSourceDependency
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        oConcept = cleaned_data["concept"]
        oDependency = cleaned_data["depends_on_source"]
        if oConcept.collection.dataset != oDependency.collection.dataset:
            msg = "The depends_on_source must be associated with the same dataset."
            self.add_error("depends_on_source", msg)


class ConceptForm(forms.ModelForm):
    class Meta:
        model = models.Concept
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        oCollection = cleaned_data["collection"]
        # validate source
        oSource = cleaned_data["source"]
        if oSource and oSource.collection != oCollection:
            msg = "The selected source must be associated with the selected collection."
            self.add_error("source", msg)
        # validate category
        oCategory = cleaned_data["category"]
        if oCategory and oCategory.dataset != oCollection.dataset:
            msg = (
                "The selected category must belong to the same dataset as the selected collection."
            )
            self.add_error("category", msg)
        # validate concept_for_prefilter
        oPrefilterConcept = cleaned_data["concept_for_prefilter"]
        if oPrefilterConcept and oPrefilterConcept.collection != oCollection:
            msg = "The concept for prefilter must belong to the same collection as this concept."
            self.add_error("concept_for_prefilter", msg)
        return None


class PermissionGroupForm(forms.ModelForm):
    class Meta:
        model = models.PermissionGroup
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        oDataset = cleaned_data["dataset"]
        # validate concept_for_allowed_subjects
        oAllowedSubjectsConcept = cleaned_data["concept_for_allowed_subjects"]
        if oAllowedSubjectsConcept:
            if oAllowedSubjectsConcept.collection.dataset != oDataset:
                msg = (
                    "The selected concept must belong to the same dataset as this "
                    "permission group."
                )
                self.add_error("concept_for_allowed_subjects", msg)
            if oAllowedSubjectsConcept.collection != oDataset.root_collection:
                msg = "The selected concept must belong to the root (subject) collection."
                self.add_error("concept_for_allowed_subjects", msg)
        # allowed concepts must be associated with same dataset
        qConcept = cleaned_data["allowed_concepts"]
        for oConcept in qConcept:
            if oConcept.collection.dataset != oDataset:
                msg = "Can only grant permissions on concepts from the same dataset."
                self.add_error("allowed_concepts", msg)
                # only append the error message once
                break
        # allowed categories must be associated with same dataset
        qCategory = cleaned_data["allowed_data_categories"]
        for oCategory in qCategory:
            if oCategory.dataset != oDataset:
                msg = "Can only grant permissions on categories from the same dataset."
                self.add_error("allowed_data_categories", msg)
                # only append the error message once
                break
        # allowed collections must be associated with same dataset
        qCollection = cleaned_data["allowed_collections"]
        for oCollection in qCollection:
            if oCollection.dataset != oDataset:
                msg = "Can only grant permissions on collections from the same dataset."
                self.add_error("allowed_collections", msg)
                # only append the error message once
                break
        return None
