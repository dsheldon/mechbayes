# `config.json`

# `launch.py`

~~~ text
usage: launch.py [-h] [--config_file CONFIG_FILE]
                 [--forecast_group [FORECAST_GROUP]] [--mode {launch,collect}]
                 [--num_sundays NUM_SUNDAYS]
                 [--forecast_dates FORECAST_DATES [FORECAST_DATES ...]]
                 [--region REGION] [--places PLACES [PLACES ...]]
                 [--model_configs MODEL_CONFIGS [MODEL_CONFIGS ...]]
                 [--start START] [--output_dir OUTPUT_DIR] [--log_dir LOG_DIR]
                 [--run] [--no-run] [--sbatch] [--no-sbatch] [--sleep SLEEP]

Launch or collect forecasts (named arguments refer to config file)

optional arguments:
  -h, --help            show this help message and exit

main arguments:
  --config_file CONFIG_FILE
                        configuration file (default: config.json)
  --forecast_group [FORECAST_GROUP]
                        name of forecast group (default: None)
  --mode {launch,collect}
                        action to take (default: launch)
  --num_sundays NUM_SUNDAYS
                        forecast for last n sundays (default: 1)
  --forecast_dates FORECAST_DATES [FORECAST_DATES ...]
                        forecast for specific dates (default: [])

manually set (or override) forecast group configuration:
  --region REGION       region name (default: None)
  --places PLACES [PLACES ...]
                        places to run (overrides region) (default: None)
  --model_configs MODEL_CONFIGS [MODEL_CONFIGS ...]
                        model configuration names (default: None)
  --start START         start date (default: 2020-03-04)

optional arguments:
  --output_dir OUTPUT_DIR
                        output directory (default: results)
  --log_dir LOG_DIR     log directory (default: log)
  --run                 run model (default: True)
  --no-run              update plots without running model (default: True)
  --sbatch              launch jobs with sbatch (default: True)
  --no-sbatch           run jobs locally (default: True)
  --sleep SLEEP         time to sleep between sbatch calls (default: 0.1)
~~~
  
# `run_model.py`

~~~ text
usage: run_model.py [-h] [--start START] [--end END] [--prefix PREFIX]
                    [--no-run] [--model_config MODEL_CONFIG]
                    place

Run COVID model on one location.

positional arguments:
  place                 place to use (e.g., US state)

optional arguments:
  -h, --help            show this help message and exit
  --start START         start date
  --end END             end date
  --prefix PREFIX       path prefix for saving results
  --no-run              don't run the model (only do vis)
  --model_config MODEL_CONFIG
                        model configuration name (see config.json)
~~~


