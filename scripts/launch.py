import os
import argparse
import pandas as pd
from pathlib import Path
import time
import json

def get_config():
    try:
        with open('config.json') as json_file:
            config = json.load(json_file)
    except Exception as e:
        raise Exception("Could not parse config.json. Please check syntax.") from e
    return config

DEFAULT_REGION = 'states_and_US'
DEFAULT_MODELS = ['mb_default']
TODAY = pd.to_datetime("today").strftime('%Y-%m-%d')

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Launch forecasts')

    # Optionally specify forecast_group from config.json
    parser.add_argument('--forecast_group', nargs="?", help='forecast group (from config.json)')

    # If forecast_group is not set, the arguments can be specified on the command-line.
    # (Arguments set here override arguments from config.json)
    parser.add_argument('--region', help='region to use (see config.json)')    
    parser.add_argument('--models', nargs="+", help='models to use (see config.json)')
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
    parser.add_argument('--sleep', help="time to sleep between sbatch calls", type=float, default=0.1)
    parser.set_defaults(run=True)
    parser.set_defaults(sbatch=True)

    # Parse arguments
    args = parser.parse_args()

    root = args.root
    log = args.logdir

    models = None
    region = None
    start = None

    config = get_config()
    
    # Get forecast group configuration arguments
    if args.forecast_group:
        forecast_group = args.forecast_group
        forecast_config = config['forecast_groups'][args.forecast_group]
        models = forecast_config['models']
        region = forecast_config['region']
        start = forecast_config['start']
    else:
        forecast_group = 'none'
        
    # Set arguments based on command-line; overrides forecast_group
    models = args.models if args.models else models
    region = args.region if args.region else region
    start  = args.start  if args.start  else start    

    # Get places
    if args.places:
        places = args.places
    elif region:
        places = config['regions'][region]
    else:
        raise ValueError('Must specify forecast_group, region, or places')

    # Check that models is set either by forecast_group or argument
    if models is None:
        raise ValueError("Must specify forecast_group or models")

    # Check that start is set
    if start is None:
        raise ValueError("Must specify forecast_group or start")
    
    # Get forecast dates
    start = args.start
    if args.num_sundays:
        forecast_dates = list(pd.date_range(periods=args.num_sundays, end=TODAY, freq='W').astype(str))        
    else:
        forecast_dates = args.forecast_dates
        
    extra_args = '' if args.run else '--no-run'

    for model in models:
        for forecast_date in forecast_dates:
            prefix = f'{root}/{forecast_group}/{model}/{forecast_date}'
            print(f"prefix is {prefix}")
            
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
                    
                    #os.system(sbatch_cmd)
                    #time.sleep(args.sleep)
                    #print(sbatch_cmd)

                else:
                    print(f"Running {name}")
                    os.system(cmd)
