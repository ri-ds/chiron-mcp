import hashlib

from chiron.helpers import to_json_string


def create_cohort_def_hash(cohort_def):
    # TODO: try to give same hash for irrelevant changes like different order or entry_ids
    hash_input = to_json_string(cohort_def)
    hash_val = hashlib.md5(hash_input.encode())
    return hash_val.hexdigest()


def create_subject_permission_hash(chironuser):
    """
    Returns a unique string that can be used to determine if two users' subject permissions
    are the same. Good for determining if cached data from User A can be used for User B.
    """
    concepts = chironuser.list_concepts_for_allowed_subjects()
    if concepts is None:
        hash_input = "all"
    else:
        concept_ids = [x.permanent_id for x in concepts]
        concept_ids.sort()
        hash_input = ",".join(concept_ids)
    hash_val = hashlib.md5(hash_input.encode())
    return hash_val.hexdigest()
