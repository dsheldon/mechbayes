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
from run_util import load_config, get_method, do_publish


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

    other_args = parser.add_argument_group("other options")
    other_args.add_argument('--scores', help="compute raw scores", dest='do_scores', action='store_true', default=True)
    other_args.add_argument('--no-scores', help="update summaries without computing raw scores", dest='do_scores', action='store_false')
    other_args.set_defaults(do_scores=True)



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

    # Only eval forecast dates that have weekahead data
    forecast_dates = [d for d in forecast_dates 
                      if pd.to_datetime("today") >= pd.to_datetime(d) + pd.Timedelta("6d")]

    # First loop: write details and summary files for each model_config and forecast date
    if args.do_scores:
        for model_config_name in model_config_names:
            for forecast_date in forecast_dates:
                print(f"Scoring {model_config_name} for {forecast_date}")
                prefix = f'{output_dir}/{forecast_group}/{model_config_name}/{forecast_date}'

                # Get model instance: used to extract forecast from samples
                model_config = config['model_configs'][model_config_name]
                model_type = get_method(model_config['model'])
                score_args = forecast_config['score_args']

                pad_strategy = score_args.get('pad_strategy') or 'shift'
                num_weeks = score_args.get('num_weeks') or 4

                scores = pd.DataFrame()

                for target in score_args['targets']:

                    # score all available weeks
                    target_scores = util.score_forecast(forecast_date,
                                                         data,
                                                         places=places,
                                                         model_type=model_type,
                                                         prefix=prefix,
                                                         target=target,
                                                         freq="week",
                                                         periods=num_weeks,
                                                         pad_strategy=pad_strategy)

                    scores = pd.concat([scores, target_scores])

                summary = util.aggregate_scores(scores)

                summary.to_csv(f"{prefix}/eval.csv", float_format="%.4f", index=False)
                scores.to_csv(f"{prefix}/scores.csv", float_format="%.4f", index=False)


    # Second loop: aggregate over forecast dates and models
    print(f"Aggregating scores")
    start = forecast_dates[0]
    end = forecast_dates[-1]
    overall_summary = pd.DataFrame()
    for model_config_name in model_config_names:
        
        model_config_scores = pd.DataFrame()

        for forecast_date in forecast_dates:

            prefix = f'{output_dir}/{forecast_group}/{model_config_name}/{forecast_date}'
            print(f"Reading scores for {prefix}")
            
            scores = pd.read_csv(f"{prefix}/scores.csv")
            model_config_scores = pd.concat([model_config_scores, scores])
        
        model_config_summary = util.aggregate_scores(model_config_scores)
        model_config_summary.insert(0, 'model', model_config_name)
        model_config_summary.to_csv(f"{output_dir}/{forecast_group}/{model_config_name}/eval_{start}_{end}.csv", 
                                    float_format="%.4f",
                                    index=False)

        overall_summary = pd.concat([overall_summary, model_config_summary])

    overall_summary.to_csv(f"{output_dir}/{forecast_group}/eval_{start}_{end}.csv", 
                           float_format="%.4f",
                           index=False)

    if forecast_config['publish']:
        do_publish(output_dir, forecast_config, forecast_group)

