# Django Management Commands

Chiron uses Django's management command system to perform many tasks. 

You can get a list of all management commands with this:
```bash
python manage.py
```

You can get help on a specific management command with this:
```bash
python manage.py command_name --help
```

## Modify the data dictionary

(management-chiron-autocreate-dd)=
### chiron_autocreate_dd

```{eval-rst}
.. autoclass:: chiron.management.commands.chiron_autocreate_dd.Command
```

```{eval-rst}
.. djcommand:: chiron.management.commands.chiron_autocreate_dd
```

### chiron_merge_processors

```{eval-rst}
.. autoclass:: chiron.management.commands.chiron_merge_processors.Command
```

```{eval-rst}
.. djcommand:: chiron.management.commands.chiron_merge_processors
```

### chiron_merge_handlers

```{eval-rst}
.. autoclass:: chiron.management.commands.chiron_merge_handlers.Command
```

```{eval-rst}
.. djcommand:: chiron.management.commands.chiron_merge_handlers
```

### chiron_drop_dataset

```{eval-rst}
.. autoclass:: chiron.management.commands.chiron_drop_dataset.Command
```

```{eval-rst}
.. djcommand:: chiron.management.commands.chiron_drop_dataset
```

### chiron_set_multivalue

```{eval-rst}
.. autoclass:: chiron.management.commands.chiron_set_multivalue.Command
```

```{eval-rst}
.. djcommand:: chiron.management.commands.chiron_set_multivalue
```

## Backup/restore the data dictionary

### chiron_backup_dd

```{eval-rst}
.. autoclass:: chiron.management.commands.chiron_backup_dd.Command
```

```{eval-rst}
.. djcommand:: chiron.management.commands.chiron_backup_dd
```

### chiron_restore_dd

```{eval-rst}
.. autoclass:: chiron.management.commands.chiron_restore_dd.Command
```

```{eval-rst}
.. djcommand:: chiron.management.commands.chiron_restore_dd
```

(cmd-chiron-backup-dataset)=
### chiron_backup_dataset

```{eval-rst}
.. autoclass:: chiron.management.commands.chiron_backup_dataset.Command
```

```{eval-rst}
.. djcommand:: chiron.management.commands.chiron_backup_dataset
```

(cmd-chiron-restore-dataset)=
### chiron_restore_dataset

```{eval-rst}
.. autoclass:: chiron.management.commands.chiron_restore_dataset.Command
```

```{eval-rst}
.. djcommand:: chiron.management.commands.chiron_restore_dataset
```

## Load data to the research database

### chiron_run_etl

```{eval-rst}
.. autoclass:: chiron.management.commands.chiron_run_etl.Command
```

```{eval-rst}
.. djcommand:: chiron.management.commands.chiron_run_etl
```

### chiron_test_etl

```{eval-rst}
.. autoclass:: chiron.management.commands.chiron_test_etl.Command
```

```{eval-rst}
.. djcommand:: chiron.management.commands.chiron_test_etl
```

### chiron_copy_permission_groups

```{eval-rst}
.. autoclass:: chiron.management.commands.chiron_copy_permission_groups.Command
```

```{eval-rst}
.. djcommand:: chiron.management.commands.chiron_copy_permission_groups
```

### chiron_create_concept_search

```{eval-rst}
.. autoclass:: chiron.management.commands.chiron_create_concept_search.Command
```

```{eval-rst}
.. djcommand:: chiron.management.commands.chiron_create_concept_search
```

## Data Quality

### chiron_check_reports

```{eval-rst}
.. autoclass:: chiron.management.commands.chiron_check_reports.Command
```

```{eval-rst}
.. djcommand:: chiron.management.commands.chiron_check_reports
```

## Data Caching

### chiron_cache_concepts

```{eval-rst}
.. autoclass:: chiron.management.commands.chiron_cache_concepts.Command
```

```{eval-rst}
.. djcommand:: chiron.management.commands.chiron_cache_concepts
```

### chiron_cache_reports

```{eval-rst}
.. autoclass:: chiron.management.commands.chiron_cache_reports.Command
```

```{eval-rst}
.. djcommand:: chiron.management.commands.chiron_cache_reports
```

### chiron_clear_caches

```{eval-rst}
.. autoclass:: chiron.management.commands.chiron_clear_caches.Command
```

```{eval-rst}
.. djcommand:: chiron.management.commands.chiron_clear_caches
```

