# Folder structure

The scripts in this directory work with model runs organized hierarchically 
into folders like this:

~~~ text
Pattern: <forecast_group>/<model_config_name>/<forecast_date>
Example: US/renewal/2021-08-01
~~~

* A `forecast_group` (e.g., `US`) is defined in [config.json]() and groups
  forecasts for a set of location made by different models over time. Examples:
  * `US`: for submissions to the US forecast hub, includes US and its states and territories
  * `EU`: for EU forecast hub, includes European countries 

* `model_config_name` (e.g., `renewal`) is a named model configuration, also defined 
  in [config.json](). A forecast group can have multiple model configurations for
   comparison.

* `forecast_date` is the date the forecast is made (usually a Sunday).

One directory contains the result of a model run for all places on that
`forecast_date`, e.g., the directory `US/renewal/2021-08-01` has these contents:

~~~~ text
2021-08-01-UMass-MechBayes.csv	    Submission file
samples/			    Posterior/forecast samples for each location
summary/			    Model fit summaries for each location
vis/				    Vis files (html, png)
~~~~

Results are pushed to a web server for browsing by (selectively) copying the 
same folder structure to the web server; `samples` directories are omitted 
to save space and time copying them. 

# Running weekly forecasts

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
    
   

# config.json

The best thing to do is take a look at the [config.json]() file to understand how configuration happens.

Two important named entities are defined there:
* `model_config` (includes model name and parameters)
* `forecast_group` (includes parameters of submission files)

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
    "submit" : true,
    "submit_args": {
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


