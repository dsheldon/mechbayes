from pathlib import Path
import os
import importlib
import json
import mechbayes.jhu as jhu
import pandas as pd
import numpy as np
import mechbayes.util as util


def load_config_json():
    here = Path(__file__).parent.resolve()
    try:
        with open(f"{here}/config.json") as json_file:
            config = json.load(json_file)
    except Exception as e:
        raise Exception("Could not parse config.json. Please check syntax.") from e
    return config

def get_model_config(model_config_name):
    '''Find named model configuration in config.json, and get model name'''
    config = load_config_json()

    model_config = config['model_configs'].get(model_config_name)
    if not model_config:
        raise ValueError(f"Model config '{model_config_name}' not found in config.json")

    return model_config

def import_module_and_get_method(method_name):
    '''Given a string like foo.bar.baz where baz is a method in the
    module foo.bar, imports foo.bar and returns the method foo.bar.baz"
    '''
    module_name, method_name = method_name.rsplit('.', 1)
    module = importlib.import_module(module_name)
    method = getattr(module, method_name)
    return method


def get_resource_dir():
    repo = Path(__file__).parent.resolve().parent.resolve()
    return f"{repo}/resources"

def install_vis(prefix, places):
    print(f"Installing vis in {prefix}")

    resource_dir = get_resource_dir()
    
    # Copy index.html file
    src = f"{resource_dir}/vis/index.html";
    dst = f"{prefix}/vis/index.html";
    os.system(f"cp {src} {dst}");

    # Write places.js file
    info = jhu.get_place_info();
    json = info[info.index.isin(places)]['name'].to_json(orient='index')
    with open(f"{prefix}/vis/places.js", "w") as f:
        f.write(f'var places={json};')

def create_submission_file(prefix, forecast_date, model_config, places, submit_args):
    
    print(f"Creating submission file in {prefix}")
    samples_directory = f"{prefix}/samples"
    
    model_name = submit_args["model_name"]
    team_name = submit_args["team_name"]
    num_weeks = submit_args["num_weeks"]
    quantiles = submit_args["quantiles"]
    targets_to_run = submit_args["targets"]

    # Get a dummy model instance used to extract variables from samples files
    model_config_obj = get_model_config(model_config)
    model_constructor = import_module_and_get_method(model_config_obj['model'])
    model = model_constructor()
    
    forecast_df = pd.DataFrame()

    forecast_date = pd.to_datetime(forecast_date)
    
    for target in targets_to_run:
        target_df = generate_forecast_df(forecast_date,
                                         model,
                                         target,
                                         places,
                                         quantiles,
                                         num_weeks,
                                         samples_directory)

        forecast_df =  forecast_df.append(target_df)

    forecast_date_str = forecast_date.strftime('%Y-%m-%d')
    fname = f"{prefix}/{forecast_date_str}-{team_name}-{model_name}.csv"
    forecast_df.to_csv(fname, float_format="%.0f", index=False)


def construct_daily_df(forecast_start, forecast_samples, target):
    if target.startswith("inc"):
        t = pd.date_range(start=forecast_start,
                          periods=forecast_samples.shape[1],
                          freq='D')
        
        daily_df = pd.DataFrame(index=t, data=np.transpose(forecast_samples))
        
    elif target.startswith("cum"):
        t = pd.date_range(start=forecast_start + pd.Timedelta("1d"),
                          periods=forecast_samples.shape[1]-1,
                          freq='D')
        
        daily_df = pd.DataFrame(index=t, data=np.transpose(forecast_samples[:,:-1]))
        
    else:
        raise ValueError(f"uncrecognized target {target}")

    return daily_df
 
def resample_to_weekly(daily_df, target):
    if target.startswith("inc"):
        weekly_df = daily_df.resample("1w", closed='left', label='left').sum()
    elif target.startswith("cum"):
        weekly_df = daily_df.resample("1w", label='left', closed='left').last()#
    else:
        raise ValueError(f"uncrecognized target {target}")          
    
    weekly_df[weekly_df < 0.] = 0.
    return weekly_df 


def get_location_codes():

    resource_dir = get_resource_dir()

    '''Get US codes'''
    df = pd.read_csv(f"{resource_dir}/locations.csv")

    # for states and US: map from abbreviation in locations.csv to location
    has_abbrev = ~ df['abbreviation'].isnull()
    state_and_us_codes = {abbrev : code for abbrev, code in zip(df.loc[has_abbrev, 'abbreviation'], 
                                                                df.loc[has_abbrev, 'location'])}
    # for counties, do a merge on FIPS to subset to counties that are recognized by the hub
    #   use the index from jhu.county_info() as keys
    #   use FIPS column from JHU as location code (it is identical to location column from forecast hub)
    county_info = jhu.get_county_info()
    county_info['index'] = county_info.index
    county_info = county_info.merge(df, left_on="FIPS", right_on="location", how="inner")
    assert(county_info['FIPS'].equals(county_info['location']))
    us_county_codes = {key: fips for key, fips in zip(county_info['index'], county_info['FIPS'])}   

    '''Get EU codes'''
    df = pd.read_csv(f"{resource_dir}/locations_eu.csv")
    eu_country_codes = {name: location for name, location in zip(df['location_name'], df['location'])}
        
    return dict(state_and_us_codes, **us_county_codes, **eu_country_codes)


def generate_forecast_df(forecast_date,
                         model,
                         target,
                         places,
                         quantiles,
                         num_weeks,
                         samples_directory):

    forecast_start = forecast_date #+ pd.Timedelta("1d")

    # mapping from hub target names to mechbayes variable names
    target2var = {'inc case' : 'dy',
                  'cum case' : 'y',
                  'inc death' : 'dz',
                  'cum death' : 'z'};

    variable = target2var[target];
    
    # empty forecast data structure
    forecast = {'quantile': [],
                'target_end_date': [],
                'value': [],
                'type': [],
                'location': [],
                'target': []}

    forecast["forecast_date"] = forecast_date
    next_saturday = pd.Timedelta('6 days')

    for place in places:
        # read_samples  
        prior_samples, mcmc_samples, post_pred_samples, forecast_samples = \
            util.load_samples(f"{samples_directory}/{place}.npz")
        
        forecast_samples = model.get(forecast_samples, variable, forecast=True)
        
        daily_df = construct_daily_df(forecast_start, forecast_samples, target)
        
        weekly_df = resample_to_weekly(daily_df, target)
        
        for time, samples in weekly_df.iterrows():
            
            week_ahead = time.week - forecast_date.week + 1
            target_end_date_datetime = pd.to_datetime(time) + next_saturday
            target_end_date = target_end_date_datetime.strftime("%Y-%m-%d")
            week_ahead_target = f"{week_ahead:d} wk ahead {target}"
            
            for q in quantiles:
                prediction = np.percentile(samples, q*100)
                forecast["quantile"].append("{:.3f}".format(q))
                forecast["value"].append(prediction)
                forecast["type"].append("quantile")
                forecast["location"].append(place)
                forecast["target"].append(week_ahead_target)
                forecast["target_end_date"].append(target_end_date)
                
                if q==0.50:
                    forecast["quantile"].append("NA")
                    forecast["value"].append(prediction)
                    forecast["type"].append("point")
                    forecast["location"].append(place)
                    forecast["target"].append(week_ahead_target)
                    forecast["target_end_date"].append(target_end_date)

    forecast_df = pd.DataFrame(forecast)

    location_codes = get_location_codes()
    forecast_df['location'] = forecast_df['location'].replace(location_codes)

    return forecast_df
