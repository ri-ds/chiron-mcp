from django.core.management.base import BaseCommand

from chiron.models import AutocreatedField

from redcap_importer.models import RedcapConnection


class Command(BaseCommand):
    help = (
        "Get labels from REDCap DD and add as Chiron concept descriptions"
        " (requires redcap_importer app)."
    )

    def print_out(self, *args):
        """A wrapper for self.stdout.write() that converts anything into a string"""
        strings = []
        for arg in args:
            strings.append(str(arg))
        self.stdout.write(",".join(strings))

    def print_err(self, *args):
        """A wrapper for self.stderr.write() that converts anything into a string"""
        strings = []
        for arg in args:
            strings.append(str(arg))
        self.stderr.write(",".join(strings))

    def add_arguments(self, parser):
        parser.add_argument("redcap_connection_name")

    def handle(self, *args, **options):
        redcap_connection_name = options["redcap_connection_name"]
        oConnection = RedcapConnection.objects.get(unique_name=redcap_connection_name)
        app_name = oConnection.unique_name
        qInstrument = oConnection.projectmetadata.instrumentmetadata_set.all()
        for oInstrument in qInstrument:
            model_name = oInstrument.get_django_model_name()
            for oField in oInstrument.fieldmetadata_set.exclude(label__isnull=True):
                print("-field", oField)
                field_name = oField.get_django_field_name()
                # see if this app/model/field are loaded
                oAIF = AutocreatedField.objects.filter(
                    app=app_name,
                    model=model_name,
                    field=field_name,
                ).first()
                # select will have display_value field
                if not oAIF:
                    oAIF = AutocreatedField.objects.filter(
                        app=app_name,
                        model=model_name,
                        field="{}_display_value".format(field_name),
                    ).first()
                # multiselect will have whole separate model
                if not oAIF:
                    oAIF = AutocreatedField.objects.filter(
                        app=app_name,
                        model="{}_{}_lookup".format(model_name, field_name),
                        field="{}_display_value".format(field_name),
                    ).first()
                if oAIF:
                    oConcept = oAIF.associated_concept
                    if oConcept:
                        oConcept.description = oField.label
                        oConcept.save()
                else:
                    print("ignored", app_name, model_name, field_name)
