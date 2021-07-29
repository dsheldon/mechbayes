import numpyro
numpyro.enable_x64()

import sys
import argparse
import covid.util as util
import numpy as onp
import run

#test

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Run COVID model on one location.')

    parser.add_argument('place', help='place to use (e.g., US state)')
    
    parser.add_argument('--config_file', help='configuration file', default='config.json')    
    parser.add_argument('--start', help='start date', default='2020-03-04')
    parser.add_argument('--end', help='end date', default=None)
    parser.add_argument('--prefix', help='path prefix for saving results', default='results')
    parser.add_argument('--model_config', help='model configuration name (see config.json)')

    parser.add_argument('--run', help="run model", dest='run', action='store_true')
    parser.add_argument('--no-run', help="update plots without running model", dest='run', action='store_false')
    parser.set_defaults(run=True)

    args = parser.parse_args()

    config = run.load_config(args.config_file)
    model_config = config['model_configs'][args.model_config]
    model_type = run.import_module_and_get_method(model_config['model'])
    
    data = util.load_data()

    if args.run:
        util.run_place(data,
                       args.place,
                       start=args.start,
                       end=args.end,
                       prefix=args.prefix,
                       model_type=model_type,
                       **model_config['args'])
    
    util.gen_forecasts(data,
                       args.place,
                       start=args.start,
                       prefix=args.prefix,
                       model_type=model_type,
                       show=False)
