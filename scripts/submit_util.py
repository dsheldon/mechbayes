import numpy as np
import pandas as pd
import mechbayes.util as util
import mechbayes.jhu as jhu
from pathlib import Path
import warnings

'''Submission'''
def create_submission_file(prefix, forecast_date, model, places, submit_args):
    
    print(f"Creating submission file in {prefix}")
    samples_directory = f"{prefix}/samples"
    
    model_name = submit_args["model_name"]
    team_name = submit_args["team_name"]
    num_weeks = submit_args["num_weeks"]
    quantiles = submit_args["quantiles"]
    targets_to_run = submit_args["targets"]

    forecast_df = pd.DataFrame()

    forecast_date = pd.to_datetime(forecast_date)

    has_any_missing = False

    for target in targets_to_run:
        target_df, has_missing_place = generate_forecast_df(forecast_date,
                                                            model,
                                                            target,
                                                            places,
                                                            quantiles,
                                                            num_weeks,
                                                            samples_directory)

        has_any_missing = has_any_missing or has_missing_place

        forecast_df =  forecast_df.append(target_df)

    forecast_date_str = forecast_date.strftime('%Y-%m-%d')

    if has_any_missing:
        fname = f"{prefix}/{forecast_date_str}-{team_name}-{model_name}-error.csv"
        warnings.warn(f"Submission file incomplete. Writing partial file to {fname}")
    else:
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

    resource_dir = (Path(__file__).parent / "resources").resolve()

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


# mapping from hub target names to mechbayes variable names
target2var = {'inc case' : 'dy',
              'cum case' : 'y',
              'inc death' : 'dz',
              'cum death' : 'z'};

def generate_forecast_df(forecast_date,
                         model,
                         target,
                         places,
                         quantiles,
                         num_weeks,
                         samples_directory):

    forecast_start = forecast_date #+ pd.Timedelta("1d")

    variable_name = target2var[target];
    
    # empty forecast data structure
    forecast = {'quantile': [],
                'value': [],
                'type': [],
                'location': [],
                'target': [],
                'forecast_date': [],
                'target_end_date': []}

    forecast["forecast_date"] = forecast_date
    next_saturday = pd.Timedelta('6 days')

    has_missing_place = False

    for place in places:
        try:
            prior_samples, mcmc_samples, post_pred_samples, forecast_samples = \
                util.load_samples(f"{samples_directory}/{place}.npz")
        except Exception as e:
            warnings.warn(f"Failed to load data: {samples_directory}/{place}.npz")
            has_missing_place = True
            continue
        
        forecast_samples = model.get(forecast_samples, variable_name, forecast=True)
        
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

    return forecast_df, has_missing_place
