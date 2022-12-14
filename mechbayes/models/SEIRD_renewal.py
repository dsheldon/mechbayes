import jax
import jax.numpy as np
from jax.random import PRNGKey

import numpyro
import numpyro.distributions as dist

from ..compartment import SEIRDModel
from .util import observe, observe_nb2, LogisticRandomWalk, frozen_random_walk, clean_daily_obs
from .base import SEIRDBase

import numpy as onp


def Geometric0(mu):
    '''Geometric RV supported on 0,1,...'''
    p = 1/(1+mu)
    log_p = np.log(p)
    log_1_minus_p = np.log(1-p)
    def log_prob(k):
        return np.where(k >= 0, k * log_1_minus_p + log_p, -np.inf)
    return log_prob

def Geometric1(mu):
    '''Geometric RV supported on 1,2,...'''
    p = 1/mu
    log_p = np.log(p)
    log_1_minus_p = np.log(1-p)
    def log_prob(k):
        return np.where(k > 0, (k-1) * log_1_minus_p + log_p, -np.inf)
    return log_prob

def simulate_incidence(incidence_history, N, T, A, beta):

    A_rev = A[::-1] # to facilitate convolution inside the dynamics loop

    # Let dE(t) be newly exposed cases at time t. Then
    #
    #  dE(t) = beta * S(t)/N * (# previous cases that are infectious at time t)
    #        = beta * S(t)/N * sum_{s<t} dE(s)*A(t-s)
    #        = beta * S(t)/N * conv(incidence, A)
    #
    def scan_body(state, beta):
        # The state of the scan body is a pair:
        #
        #    dE_history   (vector) incident exposures (dE) over 
        #                 over the last CONV_WIDTH time steps
        #
        #                 S   (scalar) current number of susceptibles
        #
        dE_history, S = state
        dE = beta * S/N * np.sum(dE_history * A_rev)
        new_state = (np.append(dE_history[1:], dE), S-dE)
        return new_state, dE
    
    S_init = N - incidence_history.sum()

    T_history = len(incidence_history)
    CONV_WIDTH = len(A)
    if T_history < CONV_WIDTH:
        dE_init = np.pad(incidence_history, (CONV_WIDTH - T_history, 0))
    else:
        dE_init = incidence_history[-CONV_WIDTH:]

    _, dE = jax.lax.scan(scan_body,                    # function to be scanned
                         (dE_init, S_init),  # initial state
                         beta*np.ones(T-1))            # vector of inputs, one per time step

    incidence_history = np.append(incidence_history, dE)

    return incidence_history

def get_infection_kernel(sigma, gamma, CONV_WIDTH=80):
    '''Returns a convolution kernel for SEIR model
    
    A(t) = Pr(infectious t time units after being infected) 
    
    This is proportional to the generation interval and 
    integrates to R0. 
    
    It is obtained by convolving the pmf of the time from 
    exposure to infection and the complementary cdf of the 
    time from infection to recovery:
    
    A(t) = Pr(infectious t time units after being infected)                
         = sum_u Pr(U=u) * Pr(V >= t-u)
         
    where U is the latent period
      and V is the infectious period
    '''
    # (There's no good reason to use two different geometric distributions 
    # here except that it matched the differential equation model better)
    U_logp = Geometric0(1/sigma)
    V_logp = Geometric1(1/gamma)

    t = np.arange(CONV_WIDTH)

    U_pmf = np.exp(U_logp(t))
    V_pmf = np.exp(V_logp(t))
    V_ccdf = 1 - np.cumsum(V_pmf)

    A = np.convolve(U_pmf, V_ccdf, mode='full')[:CONV_WIDTH]

    return A

def incidence_to_infections_and_deaths(dE, sigma, gamma, death_prob, death_rate, CONV_WIDTH=80):
    '''Calculate infections and deaths from incident exposures via convolutions'''
        
    T = len(dE)

    # U = latent period
    # V = infectious period
    # W = time from leaving infectious compartment to death
    U_logp = Geometric0(1/sigma)
    V_logp = Geometric1(1/gamma)
    W_logp = Geometric0(1/death_rate)

    t = np.arange(CONV_WIDTH)

    U_pmf = np.exp(U_logp(t))
    V_pmf = np.exp(V_logp(t))
    W_pmf = np.exp(W_logp(t))
       
    dI = np.convolve(dE, U_pmf, mode='full')[:T]             # incident infections
    dH = np.convolve(death_prob*dI, V_pmf, mode='full')[:T]  # entries into first compartment of death pathway
    dD = np.convolve(dH, W_pmf, mode='full')[:T]             # incident deaths

    return dI, dD


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
                
        # Sample initial time series of exposed individuals and 
        # initial (cumulative) number of cases and deaths        
        seed_length = 10;
        dE_init = numpyro.sample("dE_init", dist.Uniform(0, 1e-4*N*np.ones(seed_length)))
        I0 = numpyro.sample("I0", dist.Uniform(0, 1e-4*N))
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


        # Split observations into first and rest
        if confirmed is None:
            confirmed0, confirmed = (None, None)
        else:
            confirmed0 = confirmed[0]  # this is cumulative number of cases by start date
            confirmed = clean_daily_obs(onp.diff(confirmed))
            
        if death is None:
            death0, death = (None, None)
        else: 
            death0 = death[0]
            death = clean_daily_obs(onp.diff(death))
        
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
                
        infections_init, deaths_init = incidence_to_infections_and_deaths(dE_init, sigma, gamma, death_prob, death_rate)
        
        # First observation
        dy0 = observe_nb2("dy0", I0, det_prob0, confirmed_dispersion, obs=confirmed0)
        dz0 = observe_nb2("dz0", D0, det_prob_d, death_dispersion, obs=death0)
               
        beta, det_prob, dE, dI, dD, dy, dz = self.dynamics(T-1, 
                                                           params, 
                                                           dE_init,
                                                           N,
                                                           num_frozen = num_frozen,
                                                           confirmed = confirmed,
                                                           death = death)

        dy = np.append(dy0, dy)
        dz = np.append(dz0, dz)

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

            beta_f, det_prob_f, dE, dI, dD, dy_f, dz_f = self.dynamics(T_future,
                                                                       params,
                                                                       dE,
                                                                       N,
                                                                       suffix = "_future")

            beta = np.append(beta, beta_f)
            det_prob = np.append(det_prob, det_prob_f)
            dy = np.append(dy, dy_f)
            dz = np.append(dz, dz_f)

        return beta, det_prob, dE, dI, dD, dy, dz
            

    def dynamics(self, T, params, dE_history, N, num_frozen=0, confirmed=None, death=None, suffix=""):
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
        
        beta = numpyro.deterministic("beta" + suffix, beta0 * np.exp(rw_scale*rw))
        
        det_prob = numpyro.sample("det_prob" + suffix,
                                  LogisticRandomWalk(loc=det_prob0, 
                                                     scale=rw_scale, 
                                                     num_steps=T))

        A = get_infection_kernel(sigma, gamma, CONV_WIDTH=40)
        dE = simulate_incidence(dE_history, N, T, A, beta)
        dI, dD = incidence_to_infections_and_deaths(dE, sigma, gamma, death_prob, death_rate, CONV_WIDTH=80)
        
        #dI = np.maximum(dI, 0.01)
        #dD = np.maximum(dD, 0.01)

        # Noisy observations
        with numpyro.handlers.scale(scale=0.5):
            dy = observe_nb2("dy" + suffix, dI[-T:], det_prob[-T:], confirmed_dispersion, obs = confirmed)

        with numpyro.handlers.scale(scale=2.0):
            dz = observe_nb2("dz" + suffix, dD[-T:], det_prob_d, death_dispersion, obs = death)

        return beta, det_prob, dE, dI, dD, dy, dz
    
