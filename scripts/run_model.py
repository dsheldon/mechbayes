import numpyro
numpyro.enable_x64()

import sys
import argparse
import mechbayes.util as util
import numpy as onp
from run_util import load_config, get_method
import data_cleaning

if __name__ == "__main__":
    
    def boolean_string(s):
      if s not in {'False', 'True'}:
          raise ValueError('Not a valid boolean string')
      return s == 'True'

    parser = argparse.ArgumentParser(description='Run forecast model for one location.')

    parser.add_argument('place', help='location (e.g., US state)')
    
    parser.add_argument('--config_file', help='configuration file (default: config.json)', default='config.json')    
    #parser.add_argument('--use_hosp_as_death', choices = [True, False], nargs="?", default=False, type = boolean_string)
    parser.add_argument('--start', help='start date', default='2020-03-04')
    parser.add_argument('--end', help='end date (i.e., forecast date)', default=None)
    parser.add_argument('--prefix', help='path prefix for saving results', default='results')
    parser.add_argument('--model_config', help='model configuration name')

    parser.add_argument('--run', help="run model", dest='run', action='store_true')
    parser.add_argument('--no-run', help="update plots without running model", dest='run', action='store_false')
    parser.set_defaults(run=True)

    args = parser.parse_args()

    config = load_config(args.config_file)
    model_config = config['model_configs'][args.model_config]
    if ('use_hosp_as_death' in model_config):
      use_hosp_as_death = boolean_string(model_config['use_hosp_as_death'])
    else:
      use_hosp_as_death = False
    model_type = get_method(model_config['model'])
    forecast_date = args.end

    data = util.load_data()
    clean_to_date = forecast_date if args.run else data['US']['data'].index[-1]
    data_cleaning.clean(data, clean_to_date)

    if args.run:
        util.run_place(data,
                       args.place,
                       use_hosp_as_death = use_hosp_as_death,
                       start=args.start,
                       end=forecast_date,
                       prefix=args.prefix,
                       model_type=model_type,
                       **model_config['args'])
    
    util.gen_forecasts(data,
                       args.place,
                       use_hosp_as_death = use_hosp_as_death,
                       start=args.start,
                       prefix=args.prefix,
                       model_type=model_type,
                       show=False)
