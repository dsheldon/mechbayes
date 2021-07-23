# Bayesian models for COVID-19

This repository contains code for Bayesian modeling of COVID-19 using [numpyro](https://github.com/pyro-ppl/numpyro) and [jax](https://github.com/google/jax).

## Models

## Team

The team is based at the [College of Information and Computer Sciences](https://www.cics.umass.edu/) and [School of Public Health & Health Sciences](https://www.umass.edu/sphhs/) at [UMass](https://www.umass.edu). The model contributors are:

* [Dan Sheldon](https://people.cs.umass.edu/~sheldon/)
* [Casey Gibson](https://gcgibson.github.io/)
* [Nick Reich](https://reichlab.io/people)

Dr. Reich directs the [CDC Influenza Forecasting Center of Excellence](https://www.umass.edu/newsoffice/article/cdc-designates-umass-amherst-flu) at UMass.

## Installation

Our code depends on numpyro and jax. If you don't have these packages, our installation routine will pull and install them:
~~~
git clone https://github.com/dsheldon/mechbayes
cd covid
pip install -e .
~~~

## Installation Details

If you need to manually install jax and numpyro, please see the instructions for those packages: [jax](https://github.com/google/jax#installation),  [numpyro](https://github.com/pyro-ppl/numpyro#installation).
