from pickle import FALSE
import sys
import traceback
import warnings

from . import jhu

import mechbayes.models.SEIRD

import pandas as pd
import matplotlib.pyplot as plt

import numpy as onp

import jax
import jax.numpy as np
from jax.random import PRNGKey

import numpyro
from numpyro.infer import MCMC, NUTS, Predictive

from pathlib import Path

import cachetools

import scipy
import scipy.stats

from .compartment import SEIRModel

from tqdm import tqdm



"""
************************************************************
Data
************************************************************
"""

def load_country_data():

    countries = jhu.load_countries()
    info = jhu.get_country_info()
    
    names = set(info.index) & set(countries.columns.unique(level=0))
    
    country_data = {
        k: {'data' : countries[k].copy(), 
            'pop' : info.loc[k, 'Population'],
            'name' : info.loc[k, 'name']}
        for k in names
    }
      
    return country_data

def load_state_data():

    states = jhu.load_us_states()
    info = jhu.get_state_info()

    names = set(info.index) & set(states.columns.unique(level=0))

    data = {
        k : {'data': states[k].copy(), 
             'pop': info.loc[k, 'Population'],
             'name': info.loc[k, 'name']
            }
        for k in names
    }
    
    return data

def load_county_data():
    US = jhu.load_us_counties()
    info = jhu.get_county_info()
    
    counties = set(info.index) & set(US.columns.unique(level=0))
    
    data = {
        k : {'data': US[k].copy(), 
             'pop': info.loc[k, 'Population'],
             'name': info.loc[k, 'name']
            }
        for k in counties
    }
    
    return data


def load_data():
    state_data = load_state_data()
    country_data = load_country_data()
    county_data = load_county_data()
    return dict(country_data, **state_data, **county_data)


def redistribute(df, date, n, k, col='death'):
    '''Redistribute n incident cases/deaths to previous k days'''
    
    # Note: modifies df in place

    # e.g., 100 incident deaths happen on day t
    #   --> n/k incident deaths on days t-k+1, t-k+2, ..., t
    #   --> n/3 incident deaths on days t-2, t-1, 2
    # 
    # the cumulative number by day t does not change
    
    ndays = onp.abs(k)
    
    a = n // ndays
    b = n % ndays
    
    new_incident = a * onp.ones(ndays)
    new_incident[:b] += 1
    
    date = pd.to_datetime(date)
    
    if k > 0:
        new_incident = onp.concatenate([new_incident, [-n]])
        #new_cumulative = onp.cumsum(new_incident)    
        end = date 
        start = date - pd.Timedelta('1d') * ndays
    else:
        new_incident = onp.concatenate([[-n], new_incident])
        #new_cumulative = onp.cumsum(new_incident)    
        start = date
        end = date + pd.Timedelta('1d') * ndays
    
    days = pd.date_range(start=start, end=end)
    #days = pd.date_range(end=date-pd.Timedelta('1d'), periods=k-1)
    
    df.loc[days, col] += new_incident


def set_trailing_weekend_zeros_to_missing(data,
                                          forecast_date,
                                          no_sunday_data_places,
                                          no_weekend_data_places):
    # Set trailing zeros to missing for places that
    # don't report on weekends. 
    #
    # This could potentially be more automated, but
    # there are issues to understand and constraints
    # on potential solutions:
    #
    # - there may be true zeros. this is rare for
    #   cases, but fairly common for deaths.
    #
    # - we may want to set non-zero values to missing,
    #   e.g., for US where counts are very low on 
    #   weekends due to most states not reporting
    #
    # - sometimes it is useful to manually adjust
    #   whether weekend data is present to help fix
    #   model fitting failures or very poor fits
    #
    # Note that we generally don't want to set _non-trailing_
    # values to missing
    #
    # - The raw data is cumulative; setting one value
    #   to nan in the middle of the time series will
    #   lead to multiple nans after differencing to get
    #   incident data.
    #
    # - Missing cases/deaths from weekends are reported later,
    #   e.g., Monday is often a big spike. In the long run, we want
    #   low counts on weekends to offset larger counts during the
    #   week to get incidence correct at the weekly level.
    
    forecast_date = pd.to_datetime(forecast_date)
    
    # Changes data in place. no return value    
    if forecast_date.dayofweek == 6: # forecast on sunday    

        sunday = forecast_date
        saturday = forecast_date - pd.Timedelta('1d')

        for place in no_sunday_data_places + no_weekend_data_places:
            data[place]['data'].loc[sunday, :] = onp.nan

        for place in no_weekend_data_places:
            data[place]['data'].loc[saturday, :] = onp.nan

    elif forecast_date.dayofweek == 5: # forecast on saturday

        saturday = forecast_date
        for place in no_weekend_data_places:
            data[place]['data'].loc[saturday, :] = onp.nan


def smooth_to_weekly(data, forecast_date, place, var, start_date, end_date=None):

    to_date = end_date or forecast_date
    
    series = data[place]['data'][var]
    
    reporting_dates = pd.date_range(start=start_date, end=to_date, freq=pd.Timedelta('1w'))

    for reporting_date in reporting_dates:
        
        # get total cases/deaths for week
        right = reporting_date
        left = reporting_date - pd.Timedelta("1w")
        cum_sum_series = onp.cumsum(series)
        cum_tot = cum_sum_series[right]
        weekly_tot = cum_sum_series[right] - cum_sum_series[left]
        
        # construct incident time series with cases/deaths
        # spread evenly through week
        avg = int(weekly_tot // 7)
        rem = int(weekly_tot % 7)        

        # set each day equal to floor(average)
        incident = avg * onp.ones(7)

        # add remainder by adding 1 for first rem days in scrambled order
        scrambled_days = [3, 0, 6, 2, 5, 4, 1]
        incident[scrambled_days[:rem]] += 1   
        
        # now reconstruct cumulative series from incident
        series[left+pd.Timedelta("1d"):right] = incident  

        cum_sum_series = onp.cumsum(series)      
        
        assert(cum_sum_series[right] - cum_sum_series[left] == weekly_tot)
        assert(cum_sum_series[right] == cum_tot)
    
    # if we didn't explicitly stop smoothing (e.g., because location
    # went back to daily reporting), assume all observations after
    # final weekly reporting date are missing
    if end_date is None and len(reporting_dates) > 0:
        last_reporting_date = reporting_dates[-1]
        series[last_reporting_date + pd.Timedelta('1d'):] = onp.nan

            
"""
************************************************************
Plotting
************************************************************
"""
    
def plot_R0(mcmc_samples, start, ax=None):

    ax = plt.axes(ax)
    
    # Compute R0 over time
    gamma = mcmc_samples['gamma'][:,None]
    beta = mcmc_samples['beta']
    t = pd.date_range(start=start, periods=beta.shape[1], freq='D')
    R0 = beta/gamma

    pi = onp.percentile(R0, (10, 90), axis=0)
    df = pd.DataFrame(index=t, data={'R0': onp.median(R0, axis=0)})
    df.plot(style='-o', ax=ax)
    ax.fill_between(t, pi[0,:], pi[1,:], alpha=0.1)

    ax.axhline(1, linestyle='--')
    

def plot_growth_rate(mcmc_samples, start, model=SEIRModel, ax=None):
    
    ax = plt.axes(ax)

    # Compute growth rate over time
    beta = mcmc_samples['beta']
    sigma = mcmc_samples['sigma'][:,None]
    gamma = mcmc_samples['gamma'][:,None]
    t = pd.date_range(start=start, periods=beta.shape[1], freq='D')

    growth_rate = SEIRModel.growth_rate((beta, sigma, gamma))

    pi = onp.percentile(growth_rate, (10, 90), axis=0)
    df = pd.DataFrame(index=t, data={'growth_rate': onp.median(growth_rate, axis=0)})
    df.plot(style='-o', ax=ax)
    ax.fill_between(t, pi[0,:], pi[1,:], alpha=0.1)

    ax.axhline(0, linestyle='--')
    


"""
************************************************************
Running
************************************************************
"""

def run_place(data, 
              place, 
              use_hosp_as_death = False,
              model_type=mechbayes.models.SEIRD.SEIRD,
              start = '2020-03-04',
              end = None,
              save = True,
              init_values = None,
              num_warmup = 1000,
              num_samples = 1000,
              num_chains = 1,
              num_prior_samples = 0,
              T_future=4*7,
              prefix = "results",
              resample_low=0,
              resample_high=100,
              save_fields=['beta0', 'beta', 'sigma', 'gamma', 'dy0', 'dy', 'dy_future', 'dz0', 'dz', 'dz_future', 'y0', 'y', 'y_future', 'z0', 'z', 'z_future' ],
              **kwargs):


    numpyro.enable_x64()

    print(f"Running {place} (start={start}, end={end})")
    place_data = data[place]['data'][start:end]
    
    # plug in hosp data as death data
    if use_hosp_as_death:
        place_data["death"] = place_data["hospitalization"]

    T = len(place_data)

    model = model_type(
        data = place_data,
        T = T,
        N = data[place]['pop'],
        **kwargs
    )
    
    print(" * running MCMC")
    mcmc_samples = model.infer(num_warmup=num_warmup, 
                               num_samples=num_samples,
                               init_values=init_values)

    if resample_low > 0 or resample_high < 100:
        print(" * resampling")
        mcmc_samples = model.resample(low=resample_low, high=resample_high, **kwargs)

    # Prior samples
    prior_samples = None
    if num_prior_samples > 0:
        print(" * collecting prior samples")
        prior_samples = model.prior(num_samples=num_prior_samples)

    # In-sample posterior predictive samples (don't condition on observations)
    print(" * collecting in-sample predictive samples")
    post_pred_samples = model.predictive()

    # Forecasting posterior predictive (do condition on observations)
    print(" * collecting forecast samples")
    forecast_samples = model.forecast(T_future=T_future)
        
    if save:

        # Save samples
        path = Path(prefix) / 'samples'
        path.mkdir(mode=0o775, parents=True, exist_ok=True)
        filename = path / f'{place}.npz'
        
        save_samples(filename,
                     prior_samples,
                     mcmc_samples, 
                     post_pred_samples,
                     forecast_samples,
                     save_fields=save_fields)
        
        path = Path(prefix) / 'summary'
        path.mkdir(mode=0o775, parents=True, exist_ok=True)
        filename = path / f'{place}.txt'
        
        write_summary(filename, model.mcmc)

        
def save_samples(filename, 
                 prior_samples,
                 mcmc_samples, 
                 post_pred_samples,
                 forecast_samples,
                 save_fields=None):
    

    def trim(d):
        if d is not None:
            d = {k : v for k, v in d.items() if k in save_fields}
        return d
        
    onp.savez_compressed(filename, 
                         prior_samples = trim(prior_samples),
                         mcmc_samples = trim(mcmc_samples),
                         post_pred_samples = trim(post_pred_samples),
                         forecast_samples = trim(forecast_samples))
    filename.chmod(0o664)


def write_summary(filename, mcmc):
    # Write diagnostics to file
    orig_stdout = sys.stdout
    with open(filename, 'w') as f:
        sys.stdout = f
        mcmc.print_summary()
    sys.stdout = orig_stdout
    filename.chmod(0o664)

    
def load_samples(filename):

    x = np.load(filename, allow_pickle=True)
    
    prior_samples = x['prior_samples'].item()
    mcmc_samples = x['mcmc_samples'].item()
    post_pred_samples = x['post_pred_samples'].item()
    forecast_samples = x['forecast_samples'].item()
    
    return prior_samples, mcmc_samples, post_pred_samples, forecast_samples


def gen_forecasts(data, 
                  place, 
                  use_hosp_as_death = False,
                  model_type=mechbayes.models.SEIRD.SEIRD,
                  start = '2020-03-04', 
                  end=None,
                  save = True,
                  show = True, 
                  prefix='results',
                  **kwargs):
    

    # Deal with paths
    samples_path = Path(prefix) / 'samples'
    vis_path = Path(prefix) / 'vis'
    vis_path.mkdir(parents=True, exist_ok=True)
    
    model = model_type()

    confirmed = data[place]['data'].confirmed[start:end]
    if use_hosp_as_death:
        death = data[place]['data'].hospitalization[start:end]
    else:
        death = data[place]['data'].death[start:end]

    T = len(confirmed)
    N = data[place]['pop']

    filename = samples_path / f'{place}.npz'   
    _, mcmc_samples, post_pred_samples, forecast_samples = load_samples(filename)
        
    for daily in [False, True]:
        for scale in ['log', 'lin']:
            for T in [28]:

                fig, axes = plt.subplots(nrows = 2, figsize=(8,12), sharex=True)    

                if daily:
                    variables = ['dy', 'dz']
                    observations = [confirmed, death]
                else:
                    variables = ['y', 'z']
                    observations= [confirmed.cumsum(), death.cumsum()]

                for variable, obs, ax in zip(variables, observations, axes):
                    model.plot_forecast(variable,
                                        post_pred_samples,
                                        forecast_samples,
                                        start,
                                        T_future=T,
                                        obs=obs,
                                        ax=ax,
                                        scale=scale)

                name = data[place]['name']
                plt.suptitle(f'{name} {T} days ')
                plt.tight_layout()

                if save:
                    filename = vis_path / f'{place}_scale_{scale}_daily_{daily}_T_{T}.png'
                    plt.savefig(filename)

                if show:
                    plt.show()
    
    fig, ax = plt.subplots(figsize=(5,4))
    plot_growth_rate(mcmc_samples, start, ax=ax)
    plt.title(place)
    plt.tight_layout()
    
    if save:
        filename = vis_path / f'{place}_R0.png'
        plt.savefig(filename)
        filename.chmod(0o664)

    if show:
        plt.show()   
        
        
        
"""
************************************************************
Performance metrics
************************************************************
"""

def construct_daily_df(forecast_date, forecast_samples, target, truth_data=None, pad_strategy="shift"):

    # Construct df indexed by time with samples in columns
    #    - starts one day after forecast date (usually Monday)
    t = pd.date_range(start=forecast_date + pd.Timedelta("1d"),
                      periods=forecast_samples.shape[1],
                      freq='D')
    daily_df = pd.DataFrame(index=t, data=np.transpose(forecast_samples))
    
    # For incident forecasts made on Sunday, pad to include a value for Sunday
    # so the first week is complete. This does not apply to forecasts made on 
    # other days because:
    #
    #  -- we will never submit a forecast on Monday for the current week, 
    #     because the data is not available until ~midnight on Monday
    # 
    #  -- forecasts submitted on Tuesday--Thursday are for the following week
    #
    if target.startswith("inc") and forecast_date.dayofweek == 6:
        if pad_strategy == "shift":
            daily_df.index -= pd.Timedelta("1d")
        elif pad_strategy == "truth":
            if truth_data is None:
                raise ValueError("Must supply truth_data with pad_strategy='truth'")
            sunday = forecast_date
            saturday = sunday - pd.Timedelta("1d")
            truth_val = np.maximum(truth_data.loc[sunday] - truth_data.loc[saturday], 0.)
            new_row = pd.DataFrame([], index=[sunday])
            daily_df = pd.concat([new_row, daily_df], ignore_index=False)
            daily_df.loc[sunday, :] = truth_val
        else:
            raise ValueError(f"Unsuported pad_strategy {pad_strategy}")

    # Always starts on forecast date
    return daily_df
 
def resample_to_weekly(daily_df, target, full_weeks=True, label="left"):
    
    if target.startswith("inc"):        
        if full_weeks:
            # truncate to start on Sunday and end on Saturday before aggregating
            start = daily_df.index[0]
            end = daily_df.index[-1]
            first_sunday = start if start.dayofweek==6 else start + pd.offsets.Week(weekday=6)        
            final_saturday = end if end.dayofweek==5 else end - pd.offsets.Week(weekday=5)

            daily_df = daily_df.loc[first_sunday:final_saturday]

        weekly_df = daily_df.resample("1w", closed='left', label=label).sum()

    elif target.startswith("cum"):

        if full_weeks:
            # truncate end on Saturday before aggregating
            end = daily_df.index[-1]
            final_saturday = end if end.dayofweek==5 else end - pd.offsets.Week(weekday=5)

            daily_df = daily_df.loc[:final_saturday]

        weekly_df = daily_df.resample("1w", closed='left', label=label).last()
    else:
        raise ValueError(f"uncrecognized target {target}")          
    
    weekly_df[weekly_df < 0.] = 0.
    return weekly_df 


def score_place(forecast_date,
                data,
                place,
                model_type=mechbayes.models.SEIRD.SEIRD,
                prefix="results",
                target="cum death",
                freq="week",
                periods=None,
                pad_strategy="shift"):

    '''Gives performance metrics for each time horizon for one place'''
    
    if target == 'cum death':
        forecast_field = 'z'
        obs_field = 'death'
    elif target == 'inc death':
        forecast_field = 'dz'
        obs_field = 'death'
    elif target == 'cum case':
        forecast_field = 'y'
        obs_field = 'confirmed'
    elif target == 'inc case':
        forecast_field = 'dy'
        obs_field = 'confirmed'
    else:
        raise ValueError(f"Invalid or unsupported target {target}")

    filename = Path(prefix) / 'samples' / f'{place}.npz'
    prior_samples, mcmc_samples, post_pred_samples, forecast_samples = \
        load_samples(filename)

    model = model_type()

    forecast_date = pd.to_datetime(forecast_date)

    # Get observed values for forecast period
    if target.startswith('cum'):
        start = forecast_date + pd.Timedelta("1d")
        obs = data[place]['data'][obs_field][start:]

    elif target.startswith('inc') and forecast_date.dayofweek==6:
        # For incident forecasts made on Sunday, also get the Sunday
        # truth data, because we will pad forecasts to include Sunday
        start = forecast_date
        obs = data[place]['data'][obs_field].diff()[start:] # incident 

    elif target.startswitch('inc'):
        start = forecast_date + pd.Timedelta("1d")
        obs = data[place]['data'][obs_field].diff()[start:] # incident 
    
    else:
        raise ValueErorr(f"bad target {target}")

    # Get daily predictions
    forecast_samples = model.get(forecast_samples, forecast_field, forecast=True)

    # Construct data frame for predictions
    samples = construct_daily_df(pd.to_datetime(forecast_date),
                                 forecast_samples, 
                                 target, 
                                 truth_data=data[place]['data'][obs_field], 
                                 pad_strategy=pad_strategy)

    # Truncate observed values and predictions to smaller length
    T = min(len(obs), samples.shape[0])
    samples = samples.iloc[:T]
    obs = obs.iloc[:T]

    # If weekly, aggregate data frames
    if freq == "week":
        samples = resample_to_weekly(samples, target, label="right")
        obs = resample_to_weekly(obs, target, label="right")
        time_unit = pd.Timedelta("1w")

        # observations are aligned to start of next week (Sunday) with pandas, so
        # subtract one day to get the target_end_date of Saturday
        target_end_date = obs.index - pd.Timedelta("1d")

    elif freq == "day":
        time_unit = pd.Timedelta("1d")
        target_end_date = obs.index
    else:
        raise ValueError(f"unreognized value for freq: {freq}")

    assert obs.index.equals(samples.index)
    target_date = obs.index
    horizon = (target_date - forecast_date)/time_unit    

    # only score the requested periods
    if periods is not None:
        obs = obs.loc[horizon <= periods]
        samples = samples.loc[horizon <= periods]
        target_end_date = target_end_date[horizon <= periods]


    # Compute metrics
    point_forecast = samples.median(axis=1)
    err = obs - point_forecast
    n_samples = samples.shape[1]
    within_100 = samples.sub(obs, axis=0).abs().lt(100)
    prob = (within_100.sum(axis=1)/n_samples)
    log_score = prob.apply(np.log).clip(lower=-10).rename('log score')
    quantile = samples.lt(obs, axis=0).sum(axis=1) / n_samples

    # Construct output data frame
    scores = pd.DataFrame( {'target' : target,
                            'forecast_date': forecast_date,
                            'target_end_date': target_end_date,
                            'time_unit' : freq,
                            'horizon' : horizon,
                            'place' : place,
                            'err' : pd.Series(obs - point_forecast, dtype='float'),
                            'log_score' : pd.Series(log_score, dtype='float'),
                            'quantile' : pd.Series(quantile, dtype='float')},
                            index=obs.index)

    return scores

def score_forecast(forecast_date,
                   data, 
                   places=None, 
                   model_type=mechbayes.models.SEIRD.SEIRD,
                   prefix="results",
                   target="inc death",
                   freq="week",
                   periods=None,
                   pad_strategy="shift"):
    
    if places is None:
        places = list(data.keys())

    # Assemble performance metrics each place and time horizon
    scores = pd.DataFrame()
    
    print(f'Scoring {target} for all places for {forecast_date} forecast')
    
    for place in tqdm(places):
        
        try:
            place_df = score_place(forecast_date,
                                   data,
                                   place,
                                   model_type=model_type,
                                   prefix=prefix,
                                   target=target,
                                   freq=freq,
                                   periods=periods,
                                   pad_strategy=pad_strategy)
        except Exception as e:
            warnings.warn(f'Could not score {place}: {e}')
            traceback.print_exc()
        else:
            scores = scores.append(place_df)

    return scores

def aggregate_scores(scores):

    # Fields are
    #   target
    #   forecast_date
    #   target_end_date
    #   time_unit
    #   horizon
    #   place
    #   err
    #   log_score
    #   quantile
    #
    # Group by
    #   target
    #   horizon
    #   
    # Aggregate
    #   err
    #   log_score
    #   quantile

    # scores = scores.copy(deep=True)
    # scores = scores[['target', 'time_unit', 'horizon', 'err', 'log_score', 'quantile']]    
    # scores['abs_err'] = scores['err'].abs()

    def myagg(s): 
        ks, pval = scipy.stats.kstest(s['quantile'], 'uniform')
        return pd.Series({
            'count': len(s),
            'signed_err' : s['err'].mean(),
            'MAE' : s['err'].abs().mean(),
            'medAE' : s['err'].abs().median(),
            'log_score' : s['log_score'].mean(),
            'KS' : ks,
            'KS_pval' : pval
        })

    summary = scores.groupby(['target', 'time_unit', 'horizon']).apply(myagg).reset_index()
    return summary
