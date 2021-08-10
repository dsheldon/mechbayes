import importlib
import json
import traceback

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

def do_publish(forecast_config):
    print(f"Publishing to web server")
    try:
        publish_args = forecast_config['publish_args']
        host = publish_args['host']
        dest = publish_args['dest']
        cmd = f"./publish.sh {output_dir} {forecast_group}/{model_config_name} {host} {dest}"
        os.system(cmd)

    except Exception:
        warnings.warn("Failed to publish to web server. Exception info:")
        traceback.print_exc()
