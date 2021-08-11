# Folder structure

The scripts in this directory work with model runs organized hierarchically 
into folders like this:

~~~ text
Pattern: <forecast_group>/<model_config_name>/<forecast_date>
Example: US/renewal/2021-08-01
~~~

* A `forecast_group` (e.g., `US`) is defined in [config.json](config.json) and groups
  forecasts for a set of location made by different models over time.
 
  Example `forecast_group`s:
  * `US`: for submissions to the US forecast hub, includes US and its states and territories
  * `EU`: for EU forecast hub, includes European countries 

* `model_config_name` (e.g., `renewal`) is a named model configuration, also defined 
  in [](config.json). A forecast group can have multiple model configurations for
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

# Running weekly forecasts

1. Edit `config.json` if needed

2. Launch forecasts

    ~~~ bash
    python launch.py --forecast_group US --num_sundays 1
    ~~~

3. Collect forecasts (creates web vis, submission files, pushes to web server)

    ~~~ bash
    python launch.py --forecast_group US --num_sundays 1 --mode collect
    ~~~

# 


# config.json

# launch.py

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


