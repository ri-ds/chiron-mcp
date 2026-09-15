from chiron import models


def drop_dataset(oDataset, keep_dataset_object=False):
    """
    Drops a single dataset and all related data from the data dictionary.
    """

    # delete CollectionRelationships
    models.CollectionRelationship.objects.filter(pk_concept__collection__dataset=oDataset).delete()

    # delete permission groups
    models.PermissionGroup.objects.filter(dataset=oDataset).delete()

    # delete dependencies
    models.SourceSourceDependency.objects.filter(source__collection__dataset=oDataset).delete()
    models.ConceptConceptDependency.objects.filter(concept__collection__dataset=oDataset).delete()
    models.ConceptSourceDependency.objects.filter(concept__collection__dataset=oDataset).delete()

    # delete concepts (plus ConceptHandlerArg)
    models.Concept.objects.filter(collection__dataset=oDataset).delete()

    # delete categories
    models.Category.objects.filter(dataset=oDataset).delete()

    # delete sources (plus SourceProcessorArg)
    models.Source.objects.filter(collection__dataset=oDataset).delete()

    # delete collections
    models.Collection.objects.filter(dataset=oDataset).delete()

    # delete AutocreatedField
    models.AutocreatedField.objects.filter(dataset=oDataset).delete()

    # delete user created content (plus ContentSharing and ContentFlag)
    if not keep_dataset_object:
        models.UserCreatedContent.objects.filter(dataset=oDataset).delete()

    # delete chiron users
    if not keep_dataset_object:
        models.ChironUser.objects.filter(dataset=oDataset).delete()

    # delete snapshots
    models.CohortDefSnapshot.objects.filter(chironuser__dataset=oDataset).delete()
    models.TableDefSnapshot.objects.filter(chironuser__dataset=oDataset).delete()
    models.AnalysisDefSnapshot.objects.filter(chironuser__dataset=oDataset).delete()

    # delete project
    if not keep_dataset_object:
        models.Project.objects.filter(dataset=oDataset).delete()

    # what about cache models?

    # delete dataset (plus DefaultTableDefConcept)'
    if not keep_dataset_object:
        oDataset.delete()
