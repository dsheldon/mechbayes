import importlib
import json
import traceback
import os

'''Utilities for running the model'''
def load_config(filename):
    try:
        with open(filename) as json_file:
            config = json.load(json_file)
    except Exception as e:
        print("Could not parse config file. Please check syntax. Exception information with deatils follows\n")
        raise(e)

    return config

def get_method(method_name):
    '''Given a string like foo.bar.baz where baz is a method in the
    module foo.bar, imports foo.bar and returns the method foo.bar.baz"
    '''
    module_name, method_name = method_name.rsplit('.', 1)
    module = importlib.import_module(module_name)
    method = getattr(module, method_name)
    return method

def do_publish(output_dir, forecast_config, forecast_group, model_config_name=None, forecast_date=None):
    print(f"Publishing to web server")
    try:
        publish_args = forecast_config['publish_args']
        host = publish_args['host']
        dest = publish_args['dest']
        
        subdir = forecast_group
        if model_config_name:
            subdir = f"{subdir}/{model_config_name}"
        if model_config_name and forecast_date:
            subdir = f"{subdir}/{forecast_date}"

        cmd = f"./publish.sh {output_dir} {subdir} {host} {dest}"
        os.system(cmd)

    except Exception:
        warnings.warn("Failed to publish to web server. Exception info:")
        traceback.print_exc()
