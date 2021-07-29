import numpyro
numpyro.enable_x64()

import sys
import argparse
import covid.util as util
import configs
import numpy as onp
import util as driver_util

#test

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Run COVID model on one location.')
    parser.add_argument('place', help='place to use (e.g., US state)')
    parser.add_argument('--start', help='start date', default='2020-03-04')
    parser.add_argument('--end', help='end date', default=None)
    parser.add_argument('--prefix', help='path prefix for saving results', default='results')
    parser.add_argument('--no-run', help="don't run the model (only do vis)", dest='run', action='store_false')
    parser.add_argument('--model_config', help='model configuration name', default='default')
    parser.set_defaults(run=True)

    args = parser.parse_args()

    data = util.load_data()

    model_config_obj = util.get_model_config(args.model_config)
    model_type = util.import_module_and_get_method(model_config_obj['model'])
    
    if args.run:
        util.run_place(data,
                       args.place,
                       start=args.start,
                       end=args.end,
                       prefix=args.prefix,
                       model_type=model_type,
                       **model_config_obj['args'])
    
    util.gen_forecasts(data,
                       args.place,
                       start=args.start,
                       prefix=args.prefix,
                       model_type=model_type,
                       show=False)
