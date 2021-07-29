import os
import argparse
import pandas as pd
from pathlib import Path
import time
import mechbayes.jhu as jhu
import util

TODAY = pd.to_datetime("today").strftime('%Y-%m-%d')

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Launch forecasts')

    # Optionally specify forecast_group from config.json
    parser.add_argument('--forecast_group', nargs="?", help='forecast group (from config.json)')

    # If forecast_group is not set, the arguments can be specified on the command-line.
    # (Arguments set here override arguments from config.json)
    parser.add_argument('--region', help='region to use (see config.json)')    
    parser.add_argument('--model_configs', nargs="+", help='named model configurations (see config.json)')
    parser.add_argument('--places',  nargs="+", help='places to run (overrides region)')
    parser.add_argument('--start', help='start date', default='2020-03-04')

    # These are always specified on the command-line
    parser.add_argument('--forecast_dates', nargs="+", help='forecast dates', default=[TODAY])
    parser.add_argument('--num_sundays', help="use the last n sundays as forecast dates", type=int, default=None)

    # Other optional arguments
    parser.add_argument('--root', help='root directory for output', default='results')
    parser.add_argument('--logdir', help='log directory', default='log')
    parser.add_argument('--no-run', help="don't run the model (only do vis)", dest='run', action='store_false')
    parser.add_argument('--no-sbatch', help="run locally instead of launching sbatch commands", dest='sbatch', action='store_false')
    parser.add_argument('--mode', help="action to take", default="launch", choices=["launch", "collect"])

    parser.add_argument('--sleep', help="time to sleep between sbatch calls", type=float, default=0.1)
    parser.set_defaults(run=True)
    parser.set_defaults(sbatch=True)
    parser.set_defaults(collect=True)

    '''Get model_configs, region, and start date. 
    
    -- If forecast_group is set, get values from config file
    -- Otherwise, use command line arguments 
    '''
    args = parser.parse_args()
    model_configs = None
    region = None
    start = None
    config = util.load_config_json()
    
    # Get forecast group configuration arguments
    if args.forecast_group:
        forecast_group = args.forecast_group
        forecast_config = config['forecast_groups'][args.forecast_group]
        model_configs = forecast_config['model_configs']
        region = forecast_config['region']
        start = forecast_config['start']
    else:
        forecast_group = 'none'
        
    # Set arguments based on command-line; overrides forecast_group
    model_configs = args.model_configs if args.model_configs else model_configs
    region = args.region if args.region else region
    start  = args.start  if args.start  else start    

    # Get places
    if args.places:
        places = args.places
    elif region:
        places = config['regions'][region]
    else:
        raise ValueError('Must specify forecast_group, region, or places')

    # Check that model_configs is set either by forecast_group or argument
    if model_configs is None:
        raise ValueError("Must specify forecast_group or model_configs")

    # Check that start is set
    if start is None:
        raise ValueError("Must specify forecast_group or start")
    
    # Get forecast dates
    start = args.start
    if args.num_sundays:
        forecast_dates = list(pd.date_range(periods=args.num_sundays, end=TODAY, freq='W').astype(str))        
    else:
        forecast_dates = args.forecast_dates

    # Other arguments
    root = args.root
    log = args.logdir
    extra_args = '' if args.run else '--no-run'

    for model_config in model_configs:
        for forecast_date in forecast_dates:
            prefix = f'{root}/{forecast_group}/{model_config}/{forecast_date}'

            if args.mode == "launch":
                for place in places:

                    name = f'{place}-{forecast_date}-{model}'
                    cmd = f'./run_model.sh "{place}" --start {start} --end {forecast_date} --model {model} --prefix {prefix} {extra_args}'
                    if args.sbatch:

                        print(f"Launching {name}")

                        logdir = f'{log}/{forecast_group}/{model}/{forecast_date}'
                        Path(logdir).mkdir(parents=True, exist_ok=True)

                        sbatch_cmd = f'sbatch ' \
                            f'--job-name="{name}" ' \
                            f'--output="{logdir}/{place}.out" ' \
                            f'--error="{logdir}/{place}.err" ' \
                            f'--nodes=1 ' \
                            f'--ntasks=1 ' \
                            f'--mem=1000 ' \
                            f'--time=04:00:00 ' \
                            f'--partition=defq ' + cmd

                        os.system(sbatch_cmd)
                        time.sleep(args.sleep)

                    else:
                        print(f"Running {name}")
                        os.system(cmd)
                        
            elif args.mode == "collect":
                
                # Install visualization
                util.install_vis(prefix, places)

                # Create submission file

                # Need model instance. Use model_config
                
                if forecast_config['submit']:
                    util.create_submission_file(prefix,
                                                forecast_date,
                                                model_config,
                                                places,
                                                forecast_config['submit_args'])

                
            else:
                raise ValueError(f"Invalid mode: {args.mode}")
