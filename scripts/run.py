import importlib
import json

'''Utilities for running the model'''
def load_config(filename):
    try:
        with open(filename) as json_file:
            config = json.load(json_file)
    except Exception as e:
        raise Exception("Could not parse config file. Please check syntax.") from e
    return config

def import_module_and_get_method(method_name):
    '''Given a string like foo.bar.baz where baz is a method in the
    module foo.bar, imports foo.bar and returns the method foo.bar.baz"
    '''
    module_name, method_name = method_name.rsplit('.', 1)
    module = importlib.import_module(module_name)
    method = getattr(module, method_name)
    return method
