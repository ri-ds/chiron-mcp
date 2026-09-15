from chiron import models
from chiron.chiron_settings import CHIRON_EVENT_CONCEPT_TYPE


class VisSchema:
    def __init__(self, dataset):
        self.dataset = dataset
        self.subject_collection = VisSubjectCollection(self.dataset)
        self.subject_relationships = []
        self.subcollections = []
        self.subrelationships = []

    def add_subcollection(self, collection_id, include_related=False):
        vis_subcollection = VisSubcollection(self.dataset, collection_id=collection_id)
        if vis_subcollection not in self.subcollections:
            self.subcollections.append(vis_subcollection)
        self.add_subject_relationship(vis_subcollection.collection)
        # also add subcollection relationships and related entities
        if include_related:
            for oRel in vis_subcollection.get_pk_relations():
                self.add_subrelationship(oRel)
            for oRel in vis_subcollection.get_fk_relations():
                self.add_subrelationship(oRel)

    def add_subject_relationship(self, oCollection):
        vis_rel = VisSubjectRelationship(oCollection)
        if vis_rel not in self.subject_relationships:
            self.subject_relationships.append(vis_rel)

    def add_all_missing_subrelationships(self):
        for oRel in models.CollectionRelationship.objects.accessible(self.dataset):
            vis_pk = VisSubcollection(self.dataset, collection=oRel.pk_concept.collection)
            vis_fk = VisSubcollection(self.dataset, collection=oRel.fk_concept.collection)
            if vis_pk in self.subcollections and vis_fk in self.subcollections:
                self.add_subrelationship(oRel)

    def add_subrelationship(self, oRel):
        pk_col = VisSubcollection(self.dataset, collection=oRel.pk_concept.collection)
        fk_col = VisSubcollection(self.dataset, collection=oRel.fk_concept.collection)
        self.add_subcollection(pk_col.collection.permanent_id)
        self.add_subcollection(fk_col.collection.permanent_id)
        vis_rel = VisSubrelationship(oRel)
        if vis_rel not in self.subrelationships:
            self.subrelationships.append(vis_rel)
        vis_col = self.get_vis_subcollection(pk_col.collection)
        vis_col.add_field("various", oRel.pk_concept.permanent_id, "PK", "subcol relationship")
        vis_col = self.get_vis_subcollection(fk_col.collection)
        comment = "link to " + pk_col.collection.permanent_id
        datatype = "various"
        if oRel.fk_concept.multivalue:
            datatype = "various[]"
        vis_col.add_field(datatype, oRel.pk_concept.permanent_id, "FK", comment)

    def get_vis_subcollection(self, collection):
        for vis_col in self.subcollections:
            if vis_col.collection == collection:
                return vis_col
        return None

    def get_mermaid_diagram(self):
        response = "erDiagram"
        response += self.subject_collection.draw_object()
        for subcol in self.subcollections:
            response += subcol.draw_object()
        for relation in self.subject_relationships:
            response += relation.draw_object()
        for relation in self.subrelationships:
            response += relation.draw_object()
        return response


class VisCollection:
    def __init__(self, dataset, collection=None, collection_id=""):
        self.dataset = dataset
        self.fields = []
        if collection:
            self.collection = collection
        if collection_id:
            oCollection = models.Collection.objects.accessible(self.dataset).get(
                permanent_id=collection_id
            )
            self.collection = oCollection

    def __eq__(self, other):
        if not isinstance(other, VisCollection):
            # don't attempt to compare against unrelated types
            return NotImplemented

        return self.collection == other.collection

    def add_field(self, datatype, name, keytype, comment):
        field = [datatype, name, keytype, comment]
        if field not in self.fields:
            self.fields.append(field)

    def draw_object(self):
        concept_count = self.collection.concept_set.accessible(self.collection.dataset).count()
        multivalue_count = (
            self.collection.concept_set.accessible(self.collection.dataset)
            .filter(multivalue=True)
            .count()
        )
        alias = f"{self.collection.permanent_id} "
        alias += f"[concepts: {concept_count} ({multivalue_count}mv)]"
        val = f'\n{self.collection.permanent_id}["{alias}"] {{'
        for field in self.fields:
            val += f'\n {field[0]} {field[1]} {field[2]} "{field[3]}"'
        val += "}"
        return val


class VisSubcollection(VisCollection):
    def __init__(self, dataset, collection=None, collection_id=""):
        super().__init__(dataset, collection, collection_id)
        subject_id_datatype = "various"
        subject_id_label = "subject_id"
        if self.collection.many_to_many_with_subject:
            subject_id_datatype = "various[]"
            subject_id_label = "subject_ids"
        self.add_field("various", "collection_id", "PK", "")
        self.add_field(subject_id_datatype, subject_id_label, "FK", "")
        if self.collection.event_date_field:
            self.add_field(
                CHIRON_EVENT_CONCEPT_TYPE,
                self.collection.event_date_field.permanent_id,
                "",
                "event date field",
            )
        if self.collection.event_end_date_field:
            self.add_field(
                CHIRON_EVENT_CONCEPT_TYPE,
                self.collection.event_end_date_field.permanent_id,
                "",
                "event end date field",
            )

    def get_pk_relations(self):
        rels = []
        for oRel in models.CollectionRelationship.objects.accessible(self.dataset):
            if oRel.pk_concept.collection == self.collection:
                rels.append(oRel)
        return rels

    def get_fk_relations(self):
        rels = []
        for oRel in models.CollectionRelationship.objects.accessible(self.dataset):
            if oRel.fk_concept.collection == self.collection:
                rels.append(oRel)
        return rels


class VisSubjectCollection(VisCollection):
    def __init__(self, dataset):
        super().__init__(dataset, dataset.root_collection)
        self.add_field("various", "subject_id", "PK", "")


class VisSubjectRelationship:
    def __init__(self, oCollection):
        self.subcollection = oCollection

    def __eq__(self, other):
        if not isinstance(other, VisSubjectRelationship):
            # don't attempt to compare against unrelated types
            return NotImplemented

        return self.subcollection == other.subcollection

    def draw_object(self):
        event_type = "non-event collection"
        if self.subcollection.event_end_date_field:
            event_type = "interval event"
        elif self.subcollection.event_date_field:
            event_type = "point event"
        rel_string = "||--o{"
        if self.subcollection.many_to_many_with_subject:
            rel_string = "}|--o{"
        subj = self.subcollection.dataset.root_collection.permanent_id
        val = f'\n{subj} {rel_string} {self.subcollection.permanent_id} : "{event_type}"'
        return val


class VisSubrelationship:
    def __init__(self, oCollectionRelationship):
        self.relationship = oCollectionRelationship

    def __eq__(self, other):
        if not isinstance(other, VisSubrelationship):
            # don't attempt to compare against unrelated types
            return NotImplemented

        return self.relationship == other.relationship

    def draw_object(self):
        pk_collection = self.relationship.pk_concept.collection.permanent_id
        fk_collection = self.relationship.fk_concept.collection.permanent_id
        rel_string = "||--o{"
        if self.relationship.fk_concept.multivalue:
            rel_string = "}o--o{"
        val = f'\n{pk_collection} {rel_string} {fk_collection} : ""'
        return val


class VisField:
    def __init__(self):
        pass
