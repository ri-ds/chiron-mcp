import importlib


def get_object_from_python_path(python_path):
    # takes python path like 'mypackage.mysubpackage.mymodule.myfunction'
    # and returns myfunction.
    # Should work for any object (functions, classes, variables, etc.)
    mod_name, object_name = python_path.rsplit(".", 1)
    mod = importlib.import_module(mod_name)
    obj = getattr(mod, object_name)
    return obj
