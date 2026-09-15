from chiron import models


def validate_data_dictionary(oDataset):
    """Check for any problems with the data dictionary for the specified dataset."""
    validation_errors = []
    validation_errors += validate_concept_id_formats(oDataset)
    validation_errors += validate_collection_id_formats(oDataset)
    validation_errors += validate_source_source_dependencies(oDataset)
    validation_errors += validate_concept_source_dependencies(oDataset)
    validation_errors += validate_concept_concept_dependencies(oDataset)
    validation_errors += validate_collection_event_concepts(oDataset)
    validation_errors += validate_collection_relationships(oDataset)
    return validation_errors


def validate_concept_id_formats(oDataset):
    """Concept.permanent_id values should not start with underscores."""
    validation_errors = []
    qConcept = models.Concept.objects.accessible(oDataset).filter(permanent_id__startswith="_")
    for oConcept in qConcept:
        validation_errors.append(
            f"Concept {oConcept} has a permanent_id that starts with "
            "an underscore. That name format is reserved for Chiron system values."
        )
    return validation_errors


def validate_collection_event_concepts(oDataset):
    """Collection event concepts cannot be multivalue."""
    validation_errors = []
    qCollection = models.Collection.objects.accessible(oDataset).filter(
        permanent_id__startswith="_"
    )
    for oCollection in qCollection:
        if oCollection.event_date_field:
            if oCollection.event_date_field.multivalue:
                oConcept = oCollection.event_date_field
                validation_errors.append(
                    f"The event_date_field concept {oConcept} for collection {oCollection} "
                    "is multivalue, but that is not allowed for collection event concepts."
                )
        if oCollection.event_end_date_field:
            if oCollection.event_end_date_field.multivalue:
                oConcept = oCollection.event_end_date_field
                validation_errors.append(
                    f"The event_end_date_field concept {oConcept} for collection {oCollection} "
                    "is multivalue, but that is not allowed for collection event concepts."
                )
    return validation_errors


def validate_collection_relationships(oDataset):
    """ConceptRelationship primary key concepts cannot be multivalue."""
    validation_errors = []
    qRelationship = models.CollectionRelationship.objects.accessible(oDataset)
    for oRelationship in qRelationship:
        if oRelationship.pk_concept.multivalue:
            oConcept = oRelationship.pk_concept
            validation_errors.append(
                f"ConceptRelationship {oRelationship} defines a primary key concept {oConcept} "
                "that is multivalue, but that is not allowed."
            )
    return validation_errors


def validate_collection_id_formats(oDataset):
    """Collection.permanent_id values should not start with underscores."""
    validation_errors = []
    qCollection = models.Collection.objects.accessible(oDataset).filter(
        permanent_id__startswith="_"
    )
    for oCollection in qCollection:
        validation_errors.append(
            f"Collection {oCollection} has a permanent_id that starts with "
            "an underscore. That name format is reserved for Chiron system values."
        )
    return validation_errors


def validate_source_source_dependencies(oDataset):
    """Sources must be loaded after sources they depend on."""
    validation_errors = []
    for oSource in models.Source.objects.accessible(oDataset):
        for oSourceSource in oSource.depends_on_sources.all():
            oDependency = oSourceSource.depends_on_source
            if oDependency.exclude_from_etl:
                validation_errors.append(
                    f"source '{oDependency}' is excluded from the ETL but required by "
                    f"source '{oSource}'"
                )
            if oDependency.execution_order >= oSource.execution_order:
                validation_errors.append(
                    f"source '{oDependency}' is required by source '{oSource}' but run afterward"
                )
    return validation_errors


def validate_concept_source_dependencies(oDataset):
    """Concepts must be loaded after sources they depend on."""
    validation_errors = []
    for oSource in models.Source.objects.accessible(oDataset):
        for oConcept in oSource.concept_set.all():
            for oConceptSource in oConcept.depends_on_sources.all():
                oDependency = oConceptSource.depends_on_source
                if oDependency.exclude_from_etl:
                    validation_errors.append(
                        f"source '{oDependency}' is excluded from the ETL but required by "
                        f"concept '{oConcept}' in source '{oSource}'"
                    )
                if oDependency.execution_order >= oSource.execution_order:
                    validation_errors.append(
                        f"source '{oDependency}' is required by concept '{oConcept}' in source "
                        f"'{oSource}' but run afterward"
                    )
    return validation_errors


def validate_concept_concept_dependencies(oDataset):
    """Concepts must be loaded after concepts they depend on."""
    validation_errors = []
    for oSource in models.Source.objects.accessible(oDataset):
        for oConcept in oSource.concept_set.all():
            for oConceptConcept in oConcept.depends_on_concepts.all():
                oDependency = oConceptConcept.depends_on_concept
                if not oDependency.published:
                    validation_errors.append(
                        f"concept {oDependency} is unpublished but required by concept "
                        f"'{oConcept}'"
                    )
                if oDependency.source.exclude_from_etl:
                    validation_errors.append(
                        f"concept '{oDependency}' is required by concept '{oConcept}' in source "
                        f"'{oSource}', but its source '{oDependency.source}' is excluded from the "
                        f"ETL"
                    )
                if oDependency.source.execution_order >= oSource.execution_order:
                    validation_errors.append(
                        f"concept '{oDependency}' is required by concept '{oConcept}' in source "
                        f"'{oSource}', but its source '{oDependency.source}' is run afterward"
                    )
    return validation_errors
