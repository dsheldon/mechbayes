# Folder structure

TODO

# Running weekly forecasts

1. Edit `config.json` if needed

2. Launch forecasts

    ~~~ bash
    python launch.py \
     --output_dir /mnt/nfs/work1/sheldon/sheldon/mechbayes-test \
     --forecast_group US \
     --num_sundays 1
    ~~~

3. Collect forecasts (creates web page and submission files)

    ~~~ bash
    python launch.py \
     --output_dir /mnt/nfs/work1/sheldon/sheldon/mechbayes-test \
     --forecast_group US \
     --num_sundays 1 \
     --collect
    ~~~

4. Publish web page, summaries, and submission files to web server.

    ~~~bash
    ./publish.sh /mnt/nfs/work1/sheldon/sheldon/mechbayes-test US
    ~~~~

    This uses rsync so only pushes files that change, but you can
    also specify individual directories, which is faster because 
    it doesn't need to scan all the files:

    ~~~ bash
    ./publish.sh /mnt/nfs/work1/sheldon/sheldon/mechbayes-test US/renewal
    ./publish.sh /mnt/nfs/work1/sheldon/sheldon/mechbayes-test US/renewal/2021-07-25
    ~~~


# config.json

# launch.py

~~~ text
usage: launch.py [-h] [--config_file CONFIG_FILE] [--mode {launch,collect}]
                 [--forecast_group FORECAST_GROUP] [--num_sundays NUM_SUNDAYS]
                 [--forecast_dates FORECAST_DATES [FORECAST_DATES ...]]
                 [--region REGION] [--places PLACES [PLACES ...]]
                 [--model_configs MODEL_CONFIGS [MODEL_CONFIGS ...]]
                 [--start START] [--output_dir OUTPUT_DIR] [--run] [--no-run]
                 [--sbatch] [--no-sbatch] [--log_dir LOG_DIR] [--sleep SLEEP]

Launch or collect forecasts (named arguments refer to config file)

optional arguments:
  -h, --help            show this help message and exit

main arguments:
  --config_file CONFIG_FILE
                        configuration file (default: config.json)
  --mode {launch,collect}
                        action to take (default: launch)
  --forecast_group FORECAST_GROUP
                        name of forecast group
  --num_sundays NUM_SUNDAYS
                        forecast for last n sundays
  --forecast_dates FORECAST_DATES [FORECAST_DATES ...]
                        forecast for specific dates

to manually set forecast group configuration options:
  --region REGION       region name
  --places PLACES [PLACES ...]
                        places to run (overrides region)
  --model_configs MODEL_CONFIGS [MODEL_CONFIGS ...]
                        model configuration names
  --start START         start date

other optional arguments:
  --output_dir OUTPUT_DIR
                        output directory
  --run                 run model (default)
  --no-run              update plots without running model
  --sbatch              launch jobs with sbatch (default)
  --no-sbatch           run jobs locally
  --log_dir LOG_DIR     log directory for sbatch jobs
  --sleep SLEEP         seconds to sleep between sbatch calls (default: 0.1)
~~~
  
# run_model.py

~~~ text
usage: run_model.py [-h] [--config_file CONFIG_FILE] [--start START]
                    [--end END] [--prefix PREFIX]
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


