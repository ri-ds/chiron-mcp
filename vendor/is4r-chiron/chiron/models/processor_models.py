import importlib

from django.db import models


#  ABSTRACT MODELS ###################################################################


class TimeStampedModel(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ####################################################################################


class Processor(models.Model):
    """
    Chiron has 4 types of processors classes that handle activity during the ETL
    and on the website. This table stores references to those classes and allows processors
    to be associated with specific Sources and Concepts in the data dictionary.

    Use the ProcessorRegistry tool to add custom processors to your project. Registered processors
    will automatically get an entry in this table, so there's no need to edit this table
    manually.
    """

    name = models.CharField(max_length=255, unique=True)
    """ Should be the name of the Python class """
    required_args = models.TextField(
        blank=True,
        null=True,
        help_text="enter argument names as comma separated list",
    )
    """ List arguments that need to be provided when this class is instantiated. """
    optional_args = models.TextField(
        blank=True,
        null=True,
        help_text="enter argument names as comma separated list",
    )
    """ List arguments that can optionally be provided when this class is instantiated. """
    is_source_processor = models.BooleanField(default=False)
    """ Set to true if this is a source processor """
    is_etl_processor = models.BooleanField(default=False)
    """ Set to true if this is an ETL processor """
    is_cohort_def_processor = models.BooleanField(default=False)
    """ Set to true if this is a cohort_def processor """
    is_display_processor = models.BooleanField(default=False)
    """ Set to true if this is a display processor """
    is_permission_processor = models.BooleanField(default=False)
    """ DEPRECATED: permission processors are no longer used. """
    # is_cohort_vis_processor = models.BooleanField(default=False)
    python_path = models.TextField(help_text='ex. "path.to.MyProcessorClass"')
    """ The full Python path to this processor. ex. 'path.to.MyProcessorClass' """
    description = models.TextField(blank=True, null=True)
    """ An optional description of this processor. """

    def __str__(self):
        # I used to list arguments, but this list has gotten too long
        # required = self.required_args if self.required_args else "[None]"
        # return "{} {}".format(self.name, required)
        return self.name

    def get_processor_class(self):
        mod_name, klass_name = self.python_path.rsplit(".", 1)
        mod = importlib.import_module(mod_name)
        Klass = getattr(mod, klass_name)
        return Klass

    def instantiate(self, *args, **kwargs):
        Klass = self.get_processor_class()
        # print(klass_name, args, kwargs)
        processor = Klass(*args, **kwargs)
        return processor

    def is_custom(self):
        if self.python_path.startswith("chiron."):
            return False
        return True


class SourceProcessorArg(models.Model):
    """
    An argument to pass to a source processor when initializing.
    Arguments are always passed as strings, though this might be changed in a future version of
    Chiron.
    """

    class DataType(models.TextChoices):
        STRING = "string", "string (enter any value, don't need quotes)"
        FLOAT = "float", "float (ex. 6.57)"
        INT = "integer", "integer (ex. 20)"
        BOOL = "boolean", "boolean/null (enter True or False or None)"

    source = models.ForeignKey("Source", on_delete=models.CASCADE)
    """ The source this argument is associated with """
    name = models.CharField(max_length=120)
    """ The variable name of the parameter """
    data_type = models.CharField(
        max_length=20,
        choices=DataType.choices,
        default=DataType.STRING,
    )
    """ What data type is the argument value? """
    value = models.TextField()
    """ The value of the argument (will be passed as a string) """

    def get_value(self):
        if self.data_type == self.DataType.STRING:
            return self.value
        if self.data_type == self.DataType.INT:
            return int(self.value)
        if self.data_type == self.DataType.FLOAT:
            return float(self.value)
        if self.data_type == self.DataType.BOOL:
            if self.value.lower() in ["none", "null"]:
                return None
            if self.value.lower() in ["true", "t"]:
                return True
            if self.value.lower() in ["false", "f"]:
                return False
        return None


class ConceptHandler(models.Model):
    """
    A wrapper class that provides an abstraction layer for the three types of processors
    for Concepts (ETL, CohortDef, and Display).
    """

    name = models.CharField(max_length=120)
    """ The name of the ConceptHandler class """
    python_path = models.TextField(help_text='ex. "path.to.MyHandlerClass"')
    """ The full python path to the concept handler class; ex. "path.to.MyHandlerClass """
    description = models.TextField(blank=True, null=True)
    """ An optional description of this ConceptHandler """

    def __str__(self):
        return self.name

    def get_processor_class(self):
        mod_name, klass_name = self.python_path.rsplit(".", 1)
        mod = importlib.import_module(mod_name)
        Klass = getattr(mod, klass_name)
        return Klass

    def instantiate(self, *args, **kwargs):
        Klass = self.get_processor_class()
        # print(klass_name, args, kwargs)
        processor = Klass(*args, **kwargs)
        return processor


class ProcessorHandlerCombo(models.Model):
    processor = models.ForeignKey(Processor, on_delete=models.CASCADE)
    handler = models.ForeignKey(ConceptHandler, on_delete=models.CASCADE)


class ConceptHandlerArg(models.Model):
    """
    An argument that will be passed when the ConceptHandler is instantiated.
    """

    class DataType(models.TextChoices):
        STRING = "string", "string (enter any value, don't need quotes)"
        FLOAT = "float", "float (ex. 6.57)"
        INT = "integer", "integer (ex. 20)"
        BOOL = "boolean", "boolean/null (enter True or False or None)"

    concept = models.ForeignKey("Concept", on_delete=models.CASCADE)
    """ The associated concept """
    name = models.CharField(max_length=120)
    """ The variable name of the argument """
    data_type = models.CharField(
        max_length=20,
        choices=DataType.choices,
        default=DataType.STRING,
    )
    """ What data type is the argument value? """
    value = models.TextField()
    """ The value to pass to the argument """

    def get_value(self):
        if self.data_type == self.DataType.STRING:
            return self.value
        if self.data_type == self.DataType.INT:
            return int(self.value)
        if self.data_type == self.DataType.FLOAT:
            return float(self.value)
        if self.data_type == self.DataType.BOOL:
            if self.value.lower() in ["none", "null"]:
                return None
            if self.value.lower() in ["true", "t"]:
                return True
            if self.value.lower() in ["false", "f"]:
                return False
        return None
