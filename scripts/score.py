import os
import argparse
import pandas as pd
from pathlib import Path
import time
import warnings
import traceback


import mechbayes.util as util

from vis_util import install_vis
from submit_util import create_submission_file
from run_util import load_config, get_method


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description='Launch or collect forecasts (named arguments refer to config file)'
    )
    
    main_args = parser.add_argument_group("main arguments")
    main_args.add_argument('--config_file', help='configuration file (default: config.json)', default='config.json')
    main_args.add_argument('--forecast_group', help='name of forecast group')
    main_args.add_argument('--num_sundays', help="forecast for last n sundays", type=int)
    main_args.add_argument('--forecast_dates', nargs="+", help='forecast for specific dates')    

    override_args = parser.add_argument_group("to manually set or override config file options")
    override_args.add_argument('--output_dir', help='output directory')
    override_args.add_argument('--model_configs', nargs="+", help='model configuration names')


    args = parser.parse_args()

    config = load_config(args.config_file)

    # output_dir
    output_dir = args.output_dir if args.output_dir else config['output_dir']
    if not output_dir:
        raise ValueError("output_dir is required")

    # forecast_group
    if not args.forecast_group:
        raise ValueError("forecast_group is required")
    forecast_group = args.forecast_group
    forecast_config = config['forecast_groups'][args.forecast_group]

    # model_config_names
    model_config_names = args.model_configs or forecast_config['model_configs']
    
    # places
    region = forecast_config['region']
    places = config['regions'][region]
    
    # forecast dates
    if args.num_sundays:
        today = pd.to_datetime("today").strftime('%Y-%m-%d')
        forecast_dates = list(pd.date_range(periods=args.num_sundays, end=today, freq='W').astype(str))
    elif args.forecast_dates:
        forecast_dates = args.forecast_dates
    else:
        raise ValueError("must specify either --forecast_dates or --num_sundays")


    data = util.load_data()

    # First loop: write details and summary files for each model_config and forecast date
    do_raw = False
    if do_raw:
        for model_config_name in model_config_names:
            for forecast_date in forecast_dates:
                prefix = f'{output_dir}/{forecast_group}/{model_config_name}/{forecast_date}'

                if pd.to_datetime("today") < pd.to_datetime(forecast_date) + pd.Timedelta("6d"):
                    continue    # no truth data availble yet

                # Get model instance: used to extract forecast from samples
                model_config = config['model_configs'][model_config_name]
                model_type = get_method(model_config['model'])
                score_args = forecast_config['score_args']

                pad_strategy = score_args.get('pad_strategy') or 'shift'
                num_weeks = score_args.get('num_weeks') or 4

                summary = pd.DataFrame()
                details = pd.DataFrame()

                for target in score_args['targets']:

                    # score all available weeks
                    target_summary, target_details = util.score_forecast(forecast_date,
                                                                         data,
                                                                         places=places,
                                                                         model_type=model_type,
                                                                         prefix=prefix,
                                                                         target=target,
                                                                         freq="week",
                                                                         periods=num_weeks,
                                                                         pad_strategy=pad_strategy)

                    summary = pd.concat([summary, target_summary])
                    details = pd.concat([details, target_details])


                path = Path(prefix) / 'eval'
                path.mkdir(parents=True, exist_ok=True)
                summary.to_csv(path / f'summary.csv', float_format="%.4f")
                details.to_csv(path / f'details.csv', float_format="%.4f")


    # Second loop: aggregate over forecast dates and models
    overall_summary = pd.DataFrame()
    for model_config_name in model_config_names:
        
        model_config_summary = pd.DataFrame()
        model_config_details = pd.DataFrame()

        for forecast_date in forecast_dates:
            if pd.to_datetime("today") < pd.to_datetime(forecast_date) + pd.Timedelta("6d"):
                continue    # no truth data availble yet

            prefix = f'{output_dir}/{forecast_group}/{model_config_name}/{forecast_date}'
            print(f"Reading scores for {prefix}")
            
            summary = pd.read_csv(f"{prefix}/eval/summary.csv")
            details = pd.read_csv(f"{prefix}/eval/details.csv")            

            model_config_summary = pd.concat([model_config_summary, summary])
            model_config_details = pd.concat([model_config_details, details])
        
        print(model_config_summary)
