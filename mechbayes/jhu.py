import pandas as pd
import cachetools.func
import warnings

from . import states

@cachetools.func.ttl_cache(ttl=600)
def load_and_massage(url):
    df = pd.read_csv(url)
    df = df.drop(columns=['Lat', 'Long'])
    df = df.rename(columns={'Province/State' : 'province', 'Country/Region' : 'country'})
    df = df.drop(columns=['province']).groupby('country').sum()
    df = df.T
    df.index = pd.to_datetime(df.index)
    return df

@cachetools.func.ttl_cache(ttl=600)
def load_countries():

    sources = {
        'confirmed' : 'https://github.com/CSSEGISandData/COVID-19/raw/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv',
        'death' : 'https://github.com/CSSEGISandData/COVID-19/raw/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv'
    }

    # Load each data file into a dataframe with row index = date, and column index = (country, province)
    d = {key: load_and_massage(url) for key, url in sources.items()}

    # Concatenate data frames: column index is now (variable, country)
    df = pd.concat(d.values(), axis=1, keys=d.keys())

    # Permute order of index to (country, province, variable) and sort the columns by the index value
    df = df.reorder_levels([1,0], axis=1).sort_index(axis=1)

    return df

def filter_counties(df):
    '''Filter to valid counties'''

    # Subset to locations: 
    #   (1) in US,
    #   (2) with county name
    
    df = df.loc[(df['iso2']=='US') & (df['Admin2']) & (df['FIPS'])].copy()
    return df

def get_place_info():
    '''Get combined metadata data frame for countries, US states, US counties'''
    country_info = get_country_info()
    state_info = get_state_info()
    county_info = get_county_info()
    return pd.concat([country_info, state_info, county_info], sort=False)

def get_country_info():
    '''Get country info from JHU location lookup file'''

    url = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/UID_ISO_FIPS_LookUp_Table.csv'
    df = pd.read_csv(url, dtype={'FIPS': object})
    df = df.loc[pd.isnull(df['Province_State'])]
    df['name'] = df['Country_Region']
    df['key'] = df['Country_Region']
    df = df.set_index('key')
    
    return df

@cachetools.func.ttl_cache(ttl=600)
def get_county_info():
    '''Get state info from JHU location lookup file'''
    
    url = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/UID_ISO_FIPS_LookUp_Table.csv'
    df = pd.read_csv(url, dtype={'FIPS': object})
    df = filter_counties(df)

    # Add county and state columns, and set key to <state abbrev>-<county name>
    df['name'] = df['Admin2'] + ', ' + df['Province_State']
    df['state'] = df['Province_State'].replace(states.abbrev)
    df['key'] = df['state'] + '-' + df['Admin2']
    df = df.set_index('key')
    return df

@cachetools.func.ttl_cache(ttl=600)
def get_state_info():
    '''Get state info from JHU location lookup file'''
    
    url = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/UID_ISO_FIPS_LookUp_Table.csv'
    df = pd.read_csv(url, dtype={'FIPS': object})
    df = df.loc[~df['FIPS'].isnull()]
    df = df.loc[df['FIPS'].astype('int') <= 78].copy() # remove counties and others
    df['name'] = df['Province_State']
    df['key'] = df['Province_State'].replace(states.abbrev)
    df = df.set_index('key')
    return df


def load_us_states():
    return load_us(counties=False)
    
def load_us_counties():
    return load_us(counties=True)

@cachetools.func.ttl_cache(ttl=600)
def load_us(counties=False):
    
    baseURL = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/"

    def load_us_time_series(file):
        '''Load data in JHU US time series format (death or confirmed)'''
    
        df = pd.read_csv(baseURL + file)

        meta_cols = ['UID',
                     'Lat',
                     'Long_',
                     'iso2',
                     'iso3',
                     'code3',
                     'FIPS',
                     'Admin2',
                     'Province_State',
                     'Country_Region',
                     'Combined_Key',
                     'Population']

        meta_cols = [c for c in meta_cols if c in df.columns]

        if counties:
            # subset to valid counties, set index to <state abbrev>-<county> and drop other metadata columns
            df = filter_counties(df)
            state = df['Province_State'].replace(states.abbrev)
            county = df['Admin2']
            df = df.drop(columns=meta_cols)
            df = df.set_index(state + '-' + county)

        else:
            # group by state
            df['state'] = df['Province_State'].replace(states.abbrev)
            df = df.drop(columns=meta_cols).groupby('state').sum()

        df = df.T
        df.index = pd.to_datetime(df.index)
        
        return df

    
    confirmed = load_us_time_series("time_series_covid19_confirmed_US.csv")
    deaths = load_us_time_series("time_series_covid19_deaths_US.csv")
    
    # Combine deaths and confirmed
    df = pd.concat([deaths,confirmed],axis=1,keys=('death','confirmed'))
    df = df.reorder_levels([1,0], axis=1).sort_index(axis=1)
    
    return(df)
