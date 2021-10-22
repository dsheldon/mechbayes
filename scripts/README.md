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

* `model_configs` (e.g., `renewal`) is a named model configuration, also defined 
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

The forecasts are automatically generated and the visualizations updated on Sunday morning and Monday morning. They will be finished running by 7am. The Sunday run is a preliminary run that we use to check for outliers that may affect the forecasts. The Monday run is what we actually submit.

## Sunday: Data Cleaning

Most of the weekly data cleaning work is now automated, but it is still
useful to look for and address serious data issues on Sunday so that they are fixed in the Monday runs.

* Check the visualization of a preliminary run of this week's forecasts compared to truth data to
  look for obvious outliers in truth data that are affecting the forecasts of incident deaths.
    * You can view the forecasts at http://doppler.cs.umass.edu/covid/weekly_submission/
    * As described above, there are subfolders for the US and the EU, then the model (we typically submit `renewal` in the US and `renewal_21` in the EU), then the forecast date. From there, look at the `vis` folder and select "daily" for the target.
    * Scan through the locations and look for situations where there is an outlier **and** the forecast of deaths is visibly affected. We'll want to fix these. If the forecast of deaths is not affected, there's no need to make an adjustment to the data.
* It's also helpful to review JHU weekly report of data problems
* Keep a checklist of possible issues
* Use [Data Cleaning.ipynb](Data%20Cleaning.ipynb) on your machine to inspect issues and make fixes if needed
    * In the second code cell, set the `place` and `var` to the location and variable with a problem. Also update the `start` date to a little before the time of the outlier, and the `forecast_date` to the date of the model run.
    * After running the first couple of code cells, you should see enough output to figure out when the problem was.
    * Put fixes in [data_cleaning.py](data_cleaning.py). You'll be adding a line similar to `util.redistribute(data['AR']['data'], '2021-10-10', 167 - 17, 12*30, 'death')` to the `make_manual_adjustments` function, where:
        * You need to update `AR` with the name of the location you're correcting
        * The second argument is the date being corrected
        * The third argument is the size of the correction. In the example above, the initial reported value was 167, and we wanted 17 deaths to be reported for that date after the adjustment was made, so the size of the correction to make is `167 - 17 = 150`.
        * The fourth argument is the number of days back over which the adjustment should be distributed. In this case, we're distributing the 150 extra reported deaths over the past `12 * 30 = 360` days. To move the exess forward in time, you could provide a negative offset.
        * The last argument is the variable for which the adjustment should be made.
    * Commit your changes to `data_cleaning.py` to the main branch and push them to the mechbayes repo. You can use your favorite git UI or commands like:

    ~~~ bash
    git add data_cleaning.py
    git commit -m "update data cleaning with fix for AR"
    git push origin main
    ~~~

    * Make sure changes are propagated to where you will run the model (i.e., do a `git pull origin main` in the mechbayes repo clone on the cluster that will be used for running the models). If you're making the changes on a Sunday, this will happen automatically before the Monday morning run, so you don't need to take any action. If you're making changes on a Monday you'll have to do this manually.

## Monday: Final check and submission

 * On Monday, repeat the steps above to check over the forecasts.
    * Hopefully you will have found any data reporting problems in your check on Sunday, so you'll be able to just submit the forecasts at this point
    * If there are problems with the forecasts, you'll have to intervene in one of two ways:
        1. Fix outliers. Go through the steps above to make adjustments for any outliers. Then, re-run forecasts for any locations that had problems using steps 5c, 5e, and 5f below.
        2. Selectively replace one model's forecasts with another's. Sometimes, one model will fail for a given location and another will succeed. In that case, you can just replace the failed model's forecasts with the forecasts from the model that succeeded, using steps 5d, 5e, and 5f below.
 * Download the submission files from the appropriate model folder on Doppler
    * By default, we use `renewal` the US and `renewal_21` for the EU. The submission files can be downloaded from a folder like http://doppler.cs.umass.edu/covid/weekly_submission/US/renewal/2021-10-17/
 * Submit by making pull requests to the `covid19-forecast-hub` and `covid19-forecast-hub-europe` repositories.

## Running Forecasts
The main script for launching and collecting forecasts is `launch.py`. The basic steps are:

1. Edit `config.json` if needed

2. Launch forecasts

    ~~~ bash
    python3 launch.py --forecast_group US --num_sundays 1
    ~~~

3. Collect forecasts (creates web vis, submission files, pushes to web server)

    ~~~ bash
    python3 launch.py --forecast_group US --num_sundays 1 --mode collect
    ~~~

4. Check results on web

5. Intervene if needed to fix problems

    a. Identify problem locations (e.g., `MA` and `NY`)
    
    b. Back up samples files if you want them
    ~~~ bash
    cd /mnt/nfs/work1/eray/eray/mechbayes
    cp US/renewal/2021-08-01/samples/{MA,NY}.npz backup/
    ~~~

    c. After making fixes to outliers on your local machine, make sure you have the updates to `data_cleaning.py` and selectively re-run forecasts. Your working directory should be `~/mechbayes/scripts`. In this command, you may need to update the `forecast_group` to `US` or `EU`, the `model_configs` to whichever model variation you want to rerun (most often `renewal` for the US or `renewal_21` for the EU), and the `places` to whichever locations you need to rerun.
    ~~~ bash
    git pull origin main
    python3 launch.py --forecast_group US --num_sundays 1 --model_configs renewal --places MA NY
    ~~~

    d. Or replace samples with ones from a different model, then rerun with the `--no-run` option to re-create the forecast plots.
    ~~~ bash
    cd /mnt/nfs/work1/eray/eray/mechbayes
    cp US/frozen_21/2021-08-01/samples/{MA,NY}.npz US/renewal/2021-08-01/samples/
    cd ~/mechbayes/scripts
    python3 launch.py --forecast_group US --num_sundays 1 --model_configs renewal --places MA NY --no-run    
    ~~~
    
    e. Monitor jobs
    ~~~ bash
    squeue -u sheldon  # use your username
    tail -f log/renewal/2021-08-01/MA.err    # to monitor progress of model run; working directory is ~/mechbayes/scripts
    ~~~
    
    f. After all jobs are complete, re-collect output (to update submission file and vis); working directory is ~/mechbayes/scripts
    ~~~ bash
    python3 launch.py --forecast_group US --num_sundays 1 --model_configs renewal --mode collect    
    ~~~

    You can supply multiple model configuration names in the commands above to re-run multiple models,
    or supply none to rerun all models.
    
## After: Scoring

Once truth data is available, you can use `score.py` for evaluation. 

You will typically want to run this command once per week after new 
truth data is available:

~~~ bash
python3 score.py --forecast_group US --num_sundays 5
~~~

This scores the last 5 weekly forecasts at all available horizons. 
The most recent week is skipped because truth data is not yet available
After 5 weeks, no further truth data is available for old forecasts.


To create summary evaluations over longer time periods without rescoring
individual forecasts (which is slow), do this:

~~~ bash
python3 score.py --forecast_group US --num_sundays 10 --no-scores
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


