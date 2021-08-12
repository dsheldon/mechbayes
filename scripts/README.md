# Folder structure

The scripts in this directory work with model runs organized hierarchically 
into folders like this:

~~~ text
Pattern: <forecast_group>/<model_config_name>/<forecast_date>
Example: US/renewal/2021-08-01
~~~

* A `forecast_group` (e.g., `US`) is defined in [config.json](config.json) and groups
  forecasts for a set of locations made by different models over time. Examples:
  * `US`: for submissions to the US forecast hub, includes US and its states and territories
  * `EU`: for EU forecast hub, includes European countries 

* `model_config_name` (e.g., `renewal`) is a named model configuration, also defined 
  in [config.json](config.json). A forecast group can have multiple model configurations for
   comparison.

* `forecast_date` is the date the forecast is made (usually a Sunday).

A single directory, e.g., `US/renewal/2021-08-01` has these contents:
~~~~ text
samples/			    # Posterior/forecast samples for each location
summary/			    # Model fit summaries for each location
vis/				    # Vis files (html, png)
2021-08-01-UMass-MechBayes.csv	    # Submission file
~~~~
These comprise the output of the `renewal` model for all places from the `US`
forecast group for forecast date `2021-08-01`. 

Later, scoring information is also put in the directory:

~~~~ text
scores.csv			    # Forecast scores for each place
eval.csv			    # Summary evaluation (aggregates over places)
~~~~

Results are pushed to a web server for browsing by (selectively) copying this folder
structure to a web server (`samples` directories are omitted 
to save space/time).

# Running weekly forecasts

## Before: Data Cleaning

Most of the weekly data cleaning work is now automated, but it will probably
remain useful to look for and address serious data issues prior to running forecasts.

* Check visualization of previous week's forecasts compared to truth data to
  look for obvious outliers in truth data
* Also review JHU weekly report of data problems
* Keep a checklist of possible issues
* Use [Data Cleaning.ipynb](Data%20Cleaning.ipynb) on your machine to inspect issues and make fixes if needed
* Put fixes in [data_cleaning.py](data_cleaning.py). Make sure changes are propagated to
  where you will run the model.

## Running Forecasts
The main script for launching and collecting forecasts is `launch.py`. The basic steps are:

1. Edit `config.json` if needed

2. Launch forecasts

    ~~~ bash
    python launch.py --forecast_group US --num_sundays 1
    ~~~

3. Collect forecasts (creates web vis, submission files, pushes to web server)

    ~~~ bash
    python launch.py --forecast_group US --num_sundays 1 --mode collect
    ~~~

4. Check results on web

5. Intervene if needed to fix problems

    a. Identify problem locations (e.g., `MA` and `NY`)
    
    b. Back up samples files if you want them
    ~~~ bash
    cp US/renewal/2021-08-01/samples/{MA,NY}.npz /some/safe/location
    ~~~

    c. Selectively re-run forecasts
    ~~~ bash
    python launch.py --forecast_group US --num_sundays 1 --model_config_name renewal --places MA NY
    ~~~

    d. Or replace samples with ones from a different model, then rerun with the `--no-run` option to re-create the forecast plots.
    ~~~ bash
    cp US/frozen_21/2021-08-01/samples/{MA,NY}.npz US/renewal/2021-08-01/samples/
    python launch.py --forecast_group US --num_sundays 1 --model_config_name renewal --places MA NY --no-run    
    ~~~
    
    e. Monitor jobs
    ~~~ bash
    squeue -u sheldon  # use your username
    tail -f log/renewal/2021-08-01/MA.err    # to monitor progress of model run
    ~~~
    
    f. After all jobs are complete, re-collect output (to update submission file and vis)
    ~~~ bash
    python launch.py --forecast_group US --num_sundays 1 --model_config_name renewal --mode collect    
    ~~~

    You can supply multiple model configuration names in the commands above to re-run multiple models,
    or supply none to rerun all models.
    
## After: Scoring

Once truth data is available, you can use `score.py` for evaluation. 

You will typically want to run this command once per week after new 
truth data is available:

~~~ bash
python score.py --forecast_group US --num_sundays 5
~~~

This scores the last 5 weekly forecasts at all available horizons. 
The most week is skipped because truth data is not yet available
After 5 weeks, no further truth data is available for old forecasts.


To create summary evaluations over longer time periods without rescoring
individual forecasts (which is slow), do this:

~~~ bash
python score.py --forecast_group US --num_sundays 10 --no-scores
~~~


# config.json

The best thing to do is take a look at the [config.json](config.json) file to understand how configuration happens.

Two important named entities are defined there:
* `model_config` (includes model name and parameters)
* `forecast_group` (includes parameters of submission files)

Pay attention to two output paths:
* `output_dir`: where results are written after running jobs
* `dest` (under `publish_args` of `forecast_group`): root directory on web server

For testing, individual users probably want to customize these to point to a personal
sandbox, while for operational forecasts, multiple users may want to write to a shared
directory.

An example model configuration is:

~~~ json
"renewal": {
    "model": "mechbayes.models.SEIRD_renewal.SEIRD",
    "args"  : {
        "gamma_shape":  1000,
        "sigma_shape":  1000,
        "resample_high": 80,
        "rw_use_last": 10,
        "rw_scale": 1e-1,
        "H_duration_est": 25.0
    }
}
~~~~

It specifies the model and its arguments. 

`model` gives the constructor method of the class that implements the model:
* In this case, it is the class `SEIRD` defined in [mechbayes/models/SEIRD_renewal.py](../mechbayes/models/SEIRD_renewal.py).
* The class should inherit from `mechbayes.models.Model` (and usually from `mechbayes.models.SEIRDModel`), defined in [mechbayes/models/base.py](../mechbayes/models/base.py).


An example forecast group is:

~~~ json
"US": {
    "region": "US_and_states_sorted",
    "start" : "2020-03-04",
    "model_configs" : ["renewal", "llonger_H_fix", "frozen_21", "frozen_28"],
    "submission" : true,
    "submission_args": {
        "quantiles": [0.01, 0.025, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.45, 0.50,
                      0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 0.975, 0.99],
        "num_weeks" : 4,
        "targets" : ["inc death", "cum death"],
        "location_codes" : "US Forecast Hub",
        "team_name" : "UMass",
        "model_name" : "MechBayes"
    },
    "publish": true,
    "publish_args": {
      "host" : "doppler",
      "dest":  "/var/www/html/covid"
    }
}
~~~


# launch.py

This is the main script use for launching and collecting forecasts. The options are:

~~~ text
usage: launch.py [-h] [--config_file CONFIG_FILE] [--mode {launch,collect,test}] [--forecast_group FORECAST_GROUP]
                 [--num_sundays NUM_SUNDAYS] [--forecast_dates FORECAST_DATES [FORECAST_DATES ...]]
                 [--output_dir OUTPUT_DIR] [--region REGION] [--places PLACES [PLACES ...]]
                 [--model_configs MODEL_CONFIGS [MODEL_CONFIGS ...]] [--start START] [--run] [--no-run] [--sbatch]
                 [--no-sbatch] [--log_dir LOG_DIR] [--sleep SLEEP]

Launch or collect forecasts (named arguments refer to config file)

optional arguments:
  -h, --help            show this help message and exit

main arguments:
  --config_file CONFIG_FILE
                        configuration file (default: config.json)
  --mode {launch,collect,test}
                        action to take (default: launch)
  --forecast_group FORECAST_GROUP
                        name of forecast group
  --num_sundays NUM_SUNDAYS
                        forecast for last n sundays
  --forecast_dates FORECAST_DATES [FORECAST_DATES ...]
                        forecast for specific dates

to manually set or override config file options:
  --output_dir OUTPUT_DIR
                        output directory
  --region REGION       region name
  --places PLACES [PLACES ...]
                        places to run (overrides region)
  --model_configs MODEL_CONFIGS [MODEL_CONFIGS ...]
                        model configuration names
  --start START         start date

other optional arguments:
  --run                 run model (default)
  --no-run              update plots without running model
  --sbatch              launch jobs with sbatch (default)
  --no-sbatch           run jobs locally
  --log_dir LOG_DIR     log directory for sbatch jobs
  --sleep SLEEP         seconds to sleep between sbatch calls (default: 0.1)
~~~
  
# score.py

This script has options similar to launch.py. 

After truth data is available, it scores forecasts and populates the output 
directory with csv files with results. The results include raw scores and 
aggreate scores at different levels.

Example score files are:

~~~~ text
US/renewal/2021-08-01/scores.csv	    # Forecast scores for each place
US/renewal/2021-08-01/eval.csv 		    # Summary evaluation (aggregates over places)

US/renewal/eval_2021-06-06_2021-08-01.csv   # Summary 2021-06-06 to 2021-08-01

US/eval_2021-06-06_2021-08-01.csv           # Summary 2021-06-06 to 2021-08-01
					    # for multiple models
~~~~

The script usage is:

~~~~ text
usage: score.py [-h] [--config_file CONFIG_FILE] [--forecast_group FORECAST_GROUP]
                [--num_sundays NUM_SUNDAYS]
                [--forecast_dates FORECAST_DATES [FORECAST_DATES ...]] [--output_dir OUTPUT_DIR]
                [--model_configs MODEL_CONFIGS [MODEL_CONFIGS ...]] [--scores] [--no-scores]

Launch or collect forecasts (named arguments refer to config file)

optional arguments:
  -h, --help            show this help message and exit

main arguments:
  --config_file CONFIG_FILE
                        configuration file (default: config.json)
  --forecast_group FORECAST_GROUP
                        name of forecast group
  --num_sundays NUM_SUNDAYS
                        forecast for last n sundays
  --forecast_dates FORECAST_DATES [FORECAST_DATES ...]
                        forecast for specific dates

to manually set or override config file options:
  --output_dir OUTPUT_DIR
                        output directory
  --model_configs MODEL_CONFIGS [MODEL_CONFIGS ...]
                        model configuration names

other options:
  --scores              compute raw scores
  --no-scores           update summaries without computing raw scores
~~~~


# run_model.py

This is the script for launching one model run (on a single location and forecast date)
and is called by `launch.py`.

A user might call it directly only for model development or testing.

~~~ text
usage: run_model.py [-h] [--config_file CONFIG_FILE] [--start START] [--end END] [--prefix PREFIX]
                    [--model_config MODEL_CONFIG] [--run] [--no-run]
                    place

Run forecast model for one location.

positional arguments:
  place                 location (e.g., US state)

optional arguments:
  -h, --help            show this help message and exit
  --config_file CONFIG_FILE
                        configuration file (default: config.json)
  --start START         start date
  --end END             end date (i.e., forecast date)
  --prefix PREFIX       path prefix for saving results
  --model_config MODEL_CONFIG
                        model configuration name
  --run                 run model
  --no-run              update plots without running model
~~~


