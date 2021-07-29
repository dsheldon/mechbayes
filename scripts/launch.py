import os
import argparse
import pandas as pd
from pathlib import Path
import time
import run
import vis
import submit

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description='Launch or collect forecasts (named arguments refer to config file)',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    main_args = parser.add_argument_group("main arguments")
    main_args.add_argument('--config_file', help='configuration file', default='config.json')
    main_args.add_argument('--forecast_group', nargs="?", help='name of forecast group')
    main_args.add_argument('--mode', help="action to take", default="launch", choices=["launch", "collect"])
    main_args.add_argument('--num_sundays', help="forecast for last n sundays", type=int, default=1)
    main_args.add_argument('--forecast_dates', nargs="+", help='forecast for specific dates', default=[])    

    override_args = parser.add_argument_group("manually set (or override) forecast group configuration")
    override_args.add_argument('--region', help='region name')    
    override_args.add_argument('--places',  nargs="+", help='places to run (overrides region)')
    override_args.add_argument('--model_configs', nargs="+", help='model configuration names')
    override_args.add_argument('--start', help='start date', default='2020-03-04')


    # Other optional arguments
    other_args = parser.add_argument_group("optional arguments")
    other_args.add_argument('--output_dir', help='output directory', default='results')
    other_args.add_argument('--log_dir', help='log directory', default='log')

    other_args.add_argument('--run', help="run model", dest='run', action='store_true')
    other_args.add_argument('--no-run', help="update plots without running model", dest='run', action='store_false')
    other_args.set_defaults(run=True)

    other_args.add_argument('--sbatch', help="launch jobs with sbatch", dest='sbatch', action='store_true')
    other_args.add_argument('--no-sbatch', help="run jobs locally", dest='sbatch', action='store_false')
    other_args.set_defaults(sbatch=True)

    other_args.add_argument('--sleep', help="time to sleep between sbatch calls", type=float, default=0.1)

    '''Get model_configs, region, and start date. 
    
    -- If forecast_group is set, get values from config file
    -- Otherwise, use command line arguments 
    '''
    args = parser.parse_args()
    model_config_names = None
    region = None
    start = None
    config = run.load_config(args.config_file)
    
    # Get forecast group configuration arguments
    if args.forecast_group:
        forecast_group = args.forecast_group
        forecast_config = config['forecast_groups'][args.forecast_group]
        model_config_names = forecast_config['model_configs']
        region = forecast_config['region']
        start = forecast_config['start']
    else:
        forecast_group = 'none'
        
    # Set arguments based on command-line; overrides forecast_group
    model_config_names = args.model_configs if args.model_configs else model_config_names
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
    if model_config_names is None:
        raise ValueError("Must specify forecast_group or model_configs")

    # Check that start is set
    if start is None:
        raise ValueError("Must specify forecast_group or start")
    
    # Get forecast dates
    start = args.start
    if args.num_sundays:
        today = pd.to_datetime("today").strftime('%Y-%m-%d')
        forecast_dates = list(pd.date_range(periods=args.num_sundays, end=today, freq='W').astype(str))
    else:
        forecast_dates = args.forecast_dates

    if not forecast_dates:
        raise ValueError("must specify either --forecast_dates or --num_sundays")
        
    # Other arguments
    output_dir = args.output_dir
    log_root = args.log_dir
    extra_args = '' if args.run else '--no-run'

    for model_config_name in model_config_names:
        for forecast_date in forecast_dates:
            prefix = f'{output_dir}/{forecast_group}/{model_config_name}/{forecast_date}'

            if args.mode == "launch":
                for place in places:

                    name = f'{place}-{forecast_date}-{model_config_name}'
                    cmd = f'./run_model.sh "{place}" --config_file {args.config_file} --start {start} --end {forecast_date} --model_config {model_config_name} --prefix {prefix} {extra_args}'
                    if args.sbatch:

                        print(f"Launching {name}")

                        logdir = f'{log_root}/{forecast_group}/{model_config_name}/{forecast_date}'
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
                vis.install_vis(prefix, places)

                # Create submission file
                if forecast_config['submit']:

                    # Get dummy model instance to extract variables from samples files
                    model_config = config['model_configs'][model_config_name]
                    model_type = run.import_module_and_get_method(model_config['model'])
                    model = model_type()
                    
                    submit.create_submission_file(prefix,
                                                  forecast_date,
                                                  model,
                                                  places,
                                                  forecast_config['submit_args'])
                
            else:
                raise ValueError(f"Invalid mode: {args.mode}")
