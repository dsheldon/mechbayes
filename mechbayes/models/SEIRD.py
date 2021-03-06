import jax
import jax.numpy as np
from jax.random import PRNGKey

import numpyro
import numpyro.distributions as dist

from ..compartment import SEIRDModel
from .util import observe, observe_nb2, ExponentialRandomWalk, LogisticRandomWalk, frozen_random_walk, clean_daily_obs
from .base import SEIRDBase, getter

import numpy as onp


"""
************************************************************
SEIRD model
************************************************************
"""

class SEIRD(SEIRDBase):    
    
    def __call__(self,
                 T = 50,
                 N = 1e5,
                 T_future = 0,
                 E_duration_est = 4.0,
                 I_duration_est = 2.0,
                 H_duration_est = 10.0,
                 R0_est = 3.0,
                 beta_shape = 1.,
                 sigma_shape = 100.,
                 gamma_shape = 100.,
                 death_rate_shape = 10.,
                 det_prob_est = 0.3,
                 det_prob_conc = 50.,
                 confirmed_dispersion=0.3,
                 death_dispersion=0.3,
                 rw_scale = 2e-1,
                 death_prob_est=0.01,
                 death_prob_conc=100,
                 forecast_rw_scale = 0.,
                 num_frozen=0,
                 rw_use_last=1,
                 confirmed=None,
                 death=None):

        '''
        Stochastic SEIR model. Draws random parameters and runs dynamics.
        '''        
                
        # Sample initial number of infected individuals
        I0 = numpyro.sample("I0", dist.Uniform(0, 1e-4*N))  # change to 1e-3 if starting on 2020-03-16
        E0 = numpyro.sample("E0", dist.Uniform(0, 1e-4*N))  # change to 1e-3 if starting on 2020-03-16
        H0 = numpyro.sample("H0", dist.Uniform(0, 1e-4*N))
        D0 = numpyro.sample("D0", dist.Uniform(0, 1e-4*N))


        # Sample dispersion parameters around specified values

        death_dispersion = numpyro.sample("death_dispersion", 
                                           dist.TruncatedNormal(low=0.1,
                                                                loc=death_dispersion, 
                                                                scale=0.15))


        confirmed_dispersion = numpyro.sample("confirmed_dispersion", 
                                              dist.TruncatedNormal(low=0.1,
                                                                   loc=confirmed_dispersion, 
                                                                   scale=0.15))



        
        # Sample parameters
        sigma = numpyro.sample("sigma", 
                               dist.Gamma(sigma_shape, sigma_shape * E_duration_est))

        gamma = numpyro.sample("gamma", 
                                dist.Gamma(gamma_shape, gamma_shape * I_duration_est))


        beta0 = numpyro.sample("beta0",
                               dist.Gamma(beta_shape, beta_shape * I_duration_est/R0_est))

        det_prob0 = numpyro.sample("det_prob0", 
                                   dist.Beta(det_prob_est * det_prob_conc,
                                            (1-det_prob_est) * det_prob_conc))

        det_prob_d = numpyro.sample("det_prob_d", 
                                    dist.Beta(.9 * 100,
                                              (1-.9) * 100))

        death_prob = numpyro.sample("death_prob", 
                                    dist.Beta(death_prob_est * death_prob_conc, (1-death_prob_est) * death_prob_conc))
                                    
        death_rate = numpyro.sample("death_rate", 
                                    dist.Gamma(death_rate_shape, death_rate_shape * H_duration_est))


        x0 = SEIRDModel.seed(N=N, I=I0, E=E0, H=H0, D=D0)
        numpyro.deterministic("x0", x0)

        # Split observations into first and rest
        if confirmed is None:
            confirmed0, confirmed = (None, None)
        else:
            confirmed0 = confirmed[0]
            confirmed = clean_daily_obs(onp.diff(confirmed))
            
        if death is None:
            death0, death = (None, None)
        else: 
            death0 = death[0]
            death = clean_daily_obs(onp.diff(death))
        
        # First observation
        with numpyro.handlers.scale(scale=0.5):
            y0 = observe_nb2("dy0", x0[6], det_prob0, confirmed_dispersion, obs=confirmed0)
            
        with numpyro.handlers.scale(scale=2.0):
            z0 = observe_nb2("dz0", x0[5], det_prob_d, death_dispersion, obs=death0)

        params = (beta0, 
                  sigma, 
                  gamma, 
                  rw_scale, 
                  det_prob0, 
                  confirmed_dispersion, 
                  death_dispersion,
                  death_prob, 
                  death_rate, 
                  det_prob_d)

        beta, det_prob, x, y, z = self.dynamics(T, 
                                                params, 
                                                x0,
                                                num_frozen = num_frozen,
                                                confirmed = confirmed,
                                                death = death)

        x = np.vstack((x0, x))
        y = np.append(y0, y)
        z = np.append(z0, z)

        if T_future > 0:

            params = (beta[-rw_use_last:].mean(), 
                      sigma, 
                      gamma, 
                      forecast_rw_scale, 
                      det_prob[-rw_use_last:].mean(),
                      confirmed_dispersion, 
                      death_dispersion,
                      death_prob, 
                      death_rate, 
                      det_prob_d)

            beta_f, det_rate_rw_f, x_f, y_f, z_f = self.dynamics(T_future+1, 
                                                                 params, 
                                                                 x[-1,:],
                                                                 suffix="_future")

            x = np.vstack((x, x_f))
            y = np.append(y, y_f)
            z = np.append(z, z_f)

        return beta, x, y, z, det_prob, death_prob
    
    
    def dynamics(self, T, params, x0, num_frozen=0, confirmed=None, death=None, suffix=""):
        '''Run SEIRD dynamics for T time steps'''

        beta0, \
        sigma, \
        gamma, \
        rw_scale, \
        det_prob0, \
        confirmed_dispersion, \
        death_dispersion, \
        death_prob, \
        death_rate, \
        det_prob_d = params

        rw = frozen_random_walk("rw" + suffix,
                                num_steps=T-1,
                                num_frozen=num_frozen)
        
        beta = numpyro.deterministic("beta", beta0 * np.exp(rw_scale*rw))
        
        det_prob = numpyro.sample("det_prob" + suffix,
                                  LogisticRandomWalk(loc=det_prob0, 
                                                     scale=rw_scale, 
                                                     num_steps=T-1))

        # Run ODE
        x = SEIRDModel.run(T, x0, (beta, sigma, gamma, death_prob, death_rate))

        numpyro.deterministic("x" + suffix, x[1:])

        x_diff = np.diff(x, axis=0)
        
        # Don't let incident cases/deaths be exactly zero (or worse, negative!)
        new_cases = np.maximum(x_diff[:,6], 0.01)
        new_deaths = np.maximum(x_diff[:,5], 0.01)
        
        # Noisy observations
        with numpyro.handlers.scale(scale=0.5):
            y = observe_nb2("dy" + suffix, new_cases, det_prob, confirmed_dispersion, obs = confirmed)

        with numpyro.handlers.scale(scale=2.0):
            z = observe_nb2("dz" + suffix, new_deaths, det_prob_d, death_dispersion, obs = death)  

        
        return beta, det_prob, x, y, z
    

