import mechbayes.util as util
import pandas as pd
import numpy as onp

NO_SUNDAY_DATA = ['ME']

NO_WEEKEND_DATA = [
    'WA',
    'RI',
    'GU',
    'KS',
    'CT',
    'TN',
    'AK',
    'LA',
    'WY',
    'NC',
    'ID',
    'SD',
    'NV',
    'WV',
    'AL',
    'DC',
    'MT',
    'VT',
    'WI',
    'SC',
    'MI',
    'IL',
    'KY',
    'AR',
    'IN',
    'NH',
    'UT',
    'OR',
    'MA',
    'MN',
    'FL',
    'GA',
    'NE',
    'NM',
    'VA',
    'CO',
    'OK'
]


def clean(data, forecast_date):

    forecast_date = pd.to_datetime(forecast_date)
    
    '''Adjustments for weekly reporting irregularities. Don't need to update each week'''
    
    # Set weekends to missing
    util.set_trailing_weekend_zeros_to_missing(data,
                                               forecast_date, 
                                               NO_SUNDAY_DATA, 
                                               NO_WEEKEND_DATA)



    # Make manual adjustments
    make_manual_adjustments(data, forecast_date)
    
    # Smooth observations to weekly for states that only report once / week.
    #
    # Note: in at least one case (OK on 2021-04-07) there is a spike in the
    # daily data that needs to be adjusted before smoothing to weekly, so this 
    # step should happen after manual adjustments.
    #
    # Assume reporting happens once/week starting on the specific date. For each
    # reporting date, take the total number reported over the preceding week and 
    # spread evenly across the days
    #
    util.smooth_to_weekly(data, forecast_date, 'IA', 'confirmed', '2021-07-21')
    util.smooth_to_weekly(data, forecast_date, 'IA', 'death',     '2021-07-21')

    util.smooth_to_weekly(data, forecast_date, 'SD', 'confirmed', '2021-07-14')
    util.smooth_to_weekly(data, forecast_date, 'SD', 'death',     '2021-07-14')

    util.smooth_to_weekly(data, forecast_date, 'FL', 'confirmed', '2021-06-11')
    util.smooth_to_weekly(data, forecast_date, 'FL', 'death',     '2021-06-11')

    # OK reports cases daily, but deaths once/week
    util.smooth_to_weekly(data, forecast_date, 'OK', 'death',     '2021-03-24')
    # 01-16 TN moves to report weekly 
    util.smooth_to_weekly(data, forecast_date, 'TN', 'confirmed', '2022-01-12')
    util.smooth_to_weekly(data, forecast_date, 'TN', 'death',     '2022-01-12')

    # Manual adjustment for OK after redistributing to weekly
    # util.redistribute(data['OK']['data'], '2021-10-20', 163 - 40, 365, 'death')

    # OK death data delayed on 11/15/2021, so data for recent 11 days is 0 or NA
    # data['OK']['data']['death'][forecast_date - pd.Timedelta("11d"):] = onp.nan

    # OH death data is delayed, so recent weeks always appear as zeros. 
    
    # Set trailing two weeks to missing
    # NEEDS UPDATE ON 2022-01-30
    data['OH']['data']['death'][forecast_date - pd.Timedelta("2w"):] = onp.nan

    # MD case/death data issues
    #data['MD']['data']['confirmed'][forecast_date - pd.Timedelta("18d"):] = onp.nan
    # data['MD']['data']['death'][forecast_date - pd.Timedelta("21d"):] = onp.nan 

    # KY reporting around new year's
    #data['KY']['data']['confirmed'][forecast_date - pd.Timedelta("3d"):] = onp.nan
    #data['KY']['data']['death'][forecast_date - pd.Timedelta("3d"):] = onp.nan
    
    # MS last two days are NAs
    data['MS']['data']['confirmed'][forecast_date - pd.Timedelta("1d"):] = onp.nan
    data['MS']['data']['death'][forecast_date - pd.Timedelta("1d"):] = onp.nan
    
    # AL Jan 13-16 are NAs
    data['AL']['data']['confirmed'][forecast_date - pd.Timedelta("3d"):] = onp.nan
    data['AL']['data']['death'][forecast_date - pd.Timedelta("3d"):] = onp.nan
    
    # TN change (likely permanent since report once a week on Wed)
    data['TN']['data']['confirmed'][forecast_date - pd.Timedelta("3d"):] = onp.nan
    data['TN']['data']['death'][forecast_date - pd.Timedelta("3d"):] = onp.nan

def make_manual_adjustments(data, forecast_date):
    '''Adjustments for one-off irregularities'''
    
    ## redistributing some VA deaths based on DPH press release
    ## https://www.vdh.virginia.gov/news/2022-news-releases/omicron-surge-in-cases-leads-to-increase-in-covid-19-associated-deaths-being-added-to-the-virginia-department-of-health-covid-19-dashboards/
    ## NGR: on second thought, didn't implement these b/c it's unclear that they would ever be propogated to ground truth data.
    # util.redistribute(data['VA']['data'], '2022-02-02', 100, 30, 'death')
    # util.redistribute(data['VA']['data'], '2022-02-03', 100, 30, 'death')
    # util.redistribute(data['VA']['data'], '2022-02-04', 100, 30, 'death')


    # https://www.alaskapublic.org/2022/01/19/the-number-of-alaskan-covid-deaths-now-tops-1000/
    # 61 of 63 deaths reported on 2022-01-29 occurred before New Year
    # AK published deaths once per month
    data['AK']['data'].loc['2022-01-01':'2022-01-18','death'] += 61
    util.redistribute(data['AK']['data'], '2022-01-01', 61, 30, 'death')

    # adjustments for some states, some might not be that important but just to be safe
    util.redistribute(data['AK']['data'], '2022-01-07', 1800, 1, 'confirmed')
    util.redistribute(data['AK']['data'], '2022-01-10', 2000, 2, 'confirmed')
    util.redistribute(data['AK']['data'], '2022-01-12', 2000, 1, 'confirmed')
    util.redistribute(data['AK']['data'], '2022-01-14', 2500, 1, 'confirmed')
    # MN case spike affects death
    util.redistribute(data['MN']['data'], '2022-01-04', 1000, 1, 'confirmed')
    util.redistribute(data['MN']['data'], '2022-01-04', 1000, -1, 'confirmed')
    util.redistribute(data['MN']['data'], '2022-01-04', 7000, -3, 'confirmed')
    util.redistribute(data['MN']['data'], '2022-01-11', 2000, 1, 'confirmed')
    util.redistribute(data['MN']['data'], '2022-01-11', 13000, -3, 'confirmed')
    # fix VT death spike
    util.redistribute(data['VT']['data'], '2022-01-11', 3300, 2, 'confirmed')
    # fix OH case spike that affects death
    util.redistribute(data['OH']['data'], '2022-01-02', 18000, 1, 'confirmed')
    util.redistribute(data['OH']['data'], '2022-01-14', 20000, 14, 'confirmed')
    util.redistribute(data['OH']['data'], '2022-01-15', 22000, 7, 'confirmed')
    # NEEDS UPDATE ON 2022-01-30
    #util.redistribute(data['OH']['data'], '2022-01-08', 25, 2, 'death')
    #util.redistribute(data['OH']['data'], '2022-01-09', 15, 5, 'death')
    #util.redistribute(data['OH']['data'], '2022-01-14', 487-70, 6, 'death')

    # fix MS spike
    util.redistribute(data['MS']['data'], '2022-01-03', 17525-4500, 3, 'confirmed')
    util.redistribute(data['MS']['data'], '2022-01-11', 22221-8000, 3, 'confirmed')
    # KY adjustments
    util.redistribute(data['KY']['data'], '2022-01-03', 22912-6000, 4, 'confirmed')
    util.redistribute(data['KY']['data'], '2022-01-05', 3000, -7, 'confirmed')
    util.redistribute(data['KY']['data'], '2022-01-06', 3000, 7, 'confirmed')
    util.redistribute(data['KY']['data'], '2022-01-07', 2000, -2, 'confirmed')
    util.redistribute(data['KY']['data'], '2022-01-07', 1000, 1, 'confirmed')
    util.redistribute(data['KY']['data'], '2022-01-10', 16671-7000, 2, 'confirmed')
    util.redistribute(data['KY']['data'], '2022-01-11', 2000, 3, 'confirmed')
    util.redistribute(data['KY']['data'], '2022-01-12', 2000, 4, 'confirmed')
    util.redistribute(data['KY']['data'], '2022-01-12', 2000, 4, 'confirmed')
    util.redistribute(data['KY']['data'], '2022-01-10', 36, 2, 'death')
    util.redistribute(data['KY']['data'], '2022-01-10', 10, -1, 'death')
    # fix single spike for WA
    util.redistribute(data['WA']['data'], '2022-01-10', 47609-13000, 2, 'confirmed')
    
    # forecast date 2022-01-9 
    util.redistribute(data['WA']['data'], '2022-01-03', 33069-10000, 3, 'confirmed')
    util.redistribute(data['WA']['data'], '2021-12-27', 20494-5000, 3, 'confirmed')

    util.redistribute(data['TX']['data'], '2022-01-03', 162871-50000, 21, 'confirmed')

    util.redistribute(data['VA']['data'], '2021-12-28', 185-45, 30, 'death')

    util.redistribute(data['UT']['data'], '2022-01-05', 44-25, 7, 'death')

    util.redistribute(data['NE']['data'], '2022-01-06', 72-30, 7, 'death')

    util.redistribute(data['KY']['data'], '2022-01-03', 80, 4, 'death')

    util.redistribute(data['DE']['data'], '2022-01-07', 44-9, 7, 'death')
    util.redistribute(data['DE']['data'], '2022-01-08', 35-14, 7, 'death')


    util.redistribute(data['TN']['data'], '2021-12-27', 169, 3, 'death')
    util.redistribute(data['TN']['data'], '2021-12-28', 56, 4, 'death')
    util.redistribute(data['TN']['data'], '2021-12-30', 33, -1, 'death') # -3 reported for 12-31

    util.redistribute(data['PR']['data'], '2022-01-02', 9969, 1, 'confirmed')
    util.redistribute(data['PR']['data'], '2021-12-25', 8627, 1, 'confirmed')

    # ALL OF THESE FIXES ARE QUESTIONABLE - I gave up and set them to NA above
    util.redistribute(data['MD']['data'], '2022-01-02', 24430, 2, 'confirmed')
    util.redistribute(data['MD']['data'], '2021-12-28', 391, 23, 'death')
    util.redistribute(data['MD']['data'], '2022-01-02', 74, 2, 'death')

    util.redistribute(data['KY']['data'], '2021-12-27', 7800, 4, 'confirmed')
    util.redistribute(data['KY']['data'], '2021-12-27', 126, 4, 'death')

    # https://github.com/CSSEGISandData/COVID-19/issues/5083
    # move newly added 2100 deaths reported on 2021-12-23 to 2021-09-01
    # after this command, 2021-12-23 has a corrected daily inc death of 72
    data['TN']['data'].loc['2021-09-01':'2021-12-22','death'] += 2100
    # redistrbute to summer
    util.redistribute(data['TN']['data'], '2021-09-01', 2100, 180, 'death') 

    util.redistribute(data['NY']['data'], '2021-12-26', 41175, 1, 'confirmed')
    util.redistribute(data['MD']['data'], '2021-12-26', 16690, 2, 'confirmed')
    
    # AZ -1 on 2021-12-26
    #util.redistribute(data['AZ']['data'], '2021-12-26', -1, 1, 'death')

    util.redistribute(data['VT']['data'], '2021-11-29', 1681 - 300, 4, 'confirmed')

    util.redistribute(data['VI']['data'], '2021-12-14', 2218, -1, 'confirmed')

    # https://www.youtube.com/watch?v=AMtWWVwAbz4
    # https://spectrumlocalnews.com/me/maine/news/2021/12/17/covid-hospitalizations-continue-at-high-level
    util.redistribute(data['ME']['data'], '2021-12-16', 20, 38, 'death')
    util.redistribute(data['ME']['data'], '2021-12-17', 19, 36, 'death')

    # https://www.adn.com/alaska-news/2021/12/17/alaska-on-friday-reports-57-deaths-mostly-from-the-fall-and-408-virus-cases-over-past-2-days/
    util.redistribute(data['AK']['data'], '2021-12-17', 56, 135, 'death')

    # IA reports weekly, was off by 1 day
    util.redistribute(data['IA']['data'], '2021-12-09', 105, 1, 'death')

    # KY has an unexplained death spike on a single day, so spread it out a bit
    util.redistribute(data['KY']['data'], '2021-12-06', 198-110, 4, 'death')
    # small adjustment for NH
    util.redistribute(data['NH']['data'], '2021-12-07', 6, 1, 'death')
    # adjust WI's single-day death spike
    util.redistribute(data['WI']['data'], '2021-12-08', 126-60, 2, 'death')
    # MI adjustments for deaths added on multiple days
    util.redistribute(data['MI']['data'], '2021-11-29', 50, 4, 'death')
    util.redistribute(data['MI']['data'], '2021-12-01', 399-180, 2, 'death')
    util.redistribute(data['MI']['data'], '2021-12-03', 310-170, 2, 'death')
    util.redistribute(data['MI']['data'], '2021-12-08', 409-260, 2, 'death')
    # MD case adjustments
    util.redistribute(data['MD']['data'], '2021-11-27', 1200, 7, 'confirmed')
    util.redistribute(data['MD']['data'], '2021-12-02', 450, 4, 'confirmed')
    util.redistribute(data['MD']['data'], '2021-12-03', 650, 5, 'confirmed')
    util.redistribute(data['MD']['data'], '2021-12-04', 700, 6, 'confirmed')

    # FL reported two weeks worth of deaths in one week, manually readjusting this week
    # trying to force the trend to continue downwards, but making hand-waving calculations 
    util.redistribute(data['FL']['data'], '2021-12-03', 40, 13, 'death')
    util.redistribute(data['FL']['data'], '2021-12-02', 43, 12, 'death')
    util.redistribute(data['FL']['data'], '2021-12-01', 46, 11, 'death')
    util.redistribute(data['FL']['data'], '2021-11-30', 49, 10, 'death')
    util.redistribute(data['FL']['data'], '2021-11-29', 52, 9, 'death')
    util.redistribute(data['FL']['data'], '2021-11-28', 55, 8, 'death')
    util.redistribute(data['FL']['data'], '2021-11-27', 58, 7, 'death')

    util.redistribute(data['FL']['data'], '2021-12-03', 1400, 13, 'confirmed')
    util.redistribute(data['FL']['data'], '2021-12-02', 1500, 12, 'confirmed')
    util.redistribute(data['FL']['data'], '2021-12-01', 1600, 11, 'confirmed')
    util.redistribute(data['FL']['data'], '2021-11-30', 1700, 10, 'confirmed')
    util.redistribute(data['FL']['data'], '2021-11-29', 1800, 9, 'confirmed')
    util.redistribute(data['FL']['data'], '2021-11-28', 1900, 8, 'confirmed')
    util.redistribute(data['FL']['data'], '2021-11-27', 2000, 7, 'confirmed')


    # MD had one day of 30 deaths that may be triggering growth in death forecast
    util.redistribute(data['MD']['data'], '2021-11-27', 30-12, 3, 'death')

    # bulk report for MO on 2021-12-02, must be for a long time back!
    # 20 deaths seems about right for daily deaths at this point
    # computing the redistribution time as the difference between 2020-03-07 and 2021-12-02
    util.redistribute(data['MO']['data'], '2021-12-02', 2441-20, 634, 'death')

    # "mini-bulk" report for OK on 11-12: https://github.com/CSSEGISandData/COVID-19/issues/4906
    # i think some of this should be put in just the previous week, and some needs to be
    # distributed further back...?
    util.redistribute(data['OK']['data'], '2021-11-12', 250, 8, 'death')
    util.redistribute(data['OK']['data'], '2021-11-12', 300, 28, 'death')

    # https://github.com/CSSEGISandData/COVID-19/issues/4930
    # per email from CSSE, ">6300" cases from full pandemic bulk reported
    # I'm making it 9000 to better match neighboring data
    util.redistribute(data['MO']['data'], '2021-11-18', 9000, 657, 'confirmed')

    # https://chfs.ky.gov/agencies/dph/covid19/COVID19DailyReport.pdf
    # 84 deaths reported on 2021-11-19 were from earlier
    util.redistribute(data['KY']['data'], '2021-11-19', 84, 365, 'death')

    # spread large case count for PA over the previous 5 months, leave 6000 cases
    util.redistribute(data['PA']['data'], '2021-11-13', 20320-6000, 150, 'confirmed')
   
    # spread cases across the previous 2 days that had 0
    util.redistribute(data['MN']['data'], '2021-11-01', 10434-7000, 2, 'confirmed')
    # https://content.govdelivery.com/accounts/ORDHS/bulletins/2f8912c
    util.redistribute(data['OR']['data'], '2021-11-02', 45-27, 4, 'death')
    util.redistribute(data['OR']['data'], '2021-11-03', 71-27, 4, 'death')
    util.redistribute(data['OR']['data'], '2021-11-04', 74-33, 6, 'death')
    util.redistribute(data['OR']['data'], '2021-11-04', 5, -1, 'death')
    # NH reporting issue
    util.redistribute(data['NH']['data'], '2021-10-28', 781-730, 1, 'confirmed')
    util.redistribute(data['NH']['data'], '2021-11-01', 3834-760, 4, 'confirmed')
    util.redistribute(data['NH']['data'], '2021-11-01', 500, -1, 'confirmed')
    util.redistribute(data['NH']['data'], '2021-11-02', 120, -1, 'confirmed')
    util.redistribute(data['NH']['data'], '2021-11-01', 24-6, 4, 'death')
    
    # https://www.wvtm13.com/article/alabama-health-department-covid-case-backlog-reporting/38080933#
    # there was some mention of "previous months" in article above, so choosing 90
    util.redistribute(data['AL']['data'], '2021-10-27', 7393 - 700, 90, 'confirmed')
    util.redistribute(data['AL']['data'], '2021-10-28', 2141 - 700, 90, 'confirmed')

    util.redistribute(data['NE']['data'], '2021-10-27', 3311 - 850, 4, 'confirmed')
    
    ## decided to set recent daily death to something like the moving average (5)
    ## and redistribute the days over the last 100 days (the delta period?)
    util.redistribute(data['NE']['data'], '2021-10-27', 481 - 5, 100, 'death')
    
    util.redistribute(data['OK']['data'], '2021-10-20', 1138 - 200, 365, 'death')

    util.redistribute(data['AK']['data'], '2021-10-19', 66-26, 7, 'death')

    # https://www.kark.com/news/health/coronavirus/covid-19-in-arkansas-deaths-up-by-almost-300-because-of-data-adjustment/
    util.redistribute(data['AR']['data'], '2021-10-10', 167 - 17, 12*30, 'death')
    util.redistribute(data['AR']['data'], '2021-10-11', 134 - 17, 12*30, 'death')

    util.redistribute(data['NY']['data'], '2021-08-15', 235 - 45, 30, 'death')

    util.redistribute(data['IA']['data'], '2021-07-07', 950, -1, 'confirmed')

    util.redistribute(data['AL']['data'], '2021-07-31', 8144 * 2 // 3, 2, 'confirmed')

    # JHU
    util.redistribute(data['TX']['data'], '2021-08-06', 7634, 60, 'confirmed')

    # JHU
    util.redistribute(data['WA']['data'], '2021-08-03', 3000, 30, 'confirmed')

    # https://news.delaware.gov/2021/07/30/positive-case-numbers-continue-to-rise-and-delta-variant-continues-to-dominate/
    # The 130 additional COVID-19 deaths occurred between mid-May 2020 and late June 2021
    util.redistribute(data['DE']['data'], '2021-07-30', 130, 400, 'death')

    util.redistribute(data['TN']['data'], '2021-07-16', -95, -1, 'death')
    util.redistribute(data['TN']['data'], '2021-07-18', 95, 1, 'death')
    util.redistribute(data['TN']['data'], '2021-07-19', 3, 1, 'death')

    util.redistribute(data['PR']['data'], '2021-07-31', 200, 1, 'confirmed')
    util.redistribute(data['PR']['data'], '2021-07-31', 600, 6, 'confirmed')

    util.redistribute(data['NE']['data'], '2021-07-28', 1009*4//5, 4, 'confirmed')

    util.redistribute(data['WI']['data'], '2021-07-27', -75, -1, 'death')
    util.redistribute(data['WI']['data'], '2021-07-28', 20, 5, 'death')

    util.redistribute(data['KS']['data'], '2021-07-27', 123, -1, 'death')

    # large neg. numbers on 22, then huge jump on 25
    util.redistribute(data['PR']['data'], '2021-07-22', -1011*3//4, -3, 'confirmed')
    util.redistribute(data['PR']['data'], '2021-07-25', 2792*3//4, 3, 'confirmed')
    util.redistribute(data['PR']['data'], '2021-07-22', -13*3//4, -3, 'death')
    util.redistribute(data['PR']['data'], '2021-07-25', 15*3//4, 3, 'death')

    # https://www.pressherald.com/2021/07/15/maine-reports-another-49-cases-of-covid-19-and-10-deaths/
    util.redistribute(data['ME']['data'], '2021-07-15', 10, 90, 'death')

    util.redistribute(data['AL']['data'], '2021-07-07', 1613*4//5, 5, 'confirmed')
    util.redistribute(data['AL']['data'], '2021-07-07', 29*4//5, 5, 'confirmed')

    # https://www.seattletimes.com/seattle-news/health/coronavirus-daily-news-updates-june-23-what-to-know-today-about-covid-19-in-the-seattle-area-washington-state-and-the-world-2/?utm_source=link&utm_medium=social#update-13980897
    util.redistribute(data['WA']['data'], '2021-06-23', 26, 90, 'death')

    # https://www.ksl.com/article/50193538/309-new-covid-19-cases-14-deaths-83k-vaccinations-reported-in-utah-friday
    util.redistribute(data['UT']['data'], '2021-06-25', 10, 60, 'death')

    util.redistribute(data['WA']['data'], '2021-06-14', -38, 90, 'death')

    # JHU
    util.redistribute(data['AK']['data'], '2021-06-11', 4, 30, 'death')

    # https://dhhr.wv.gov/News/2021/Pages/COVID-19-Daily-Update-6-9-2021.aspx
    util.redistribute(data['WV']['data'], '2021-06-09', 24, 90, 'death')

    util.redistribute(data['WA']['data'], '2021-06-08', -81, 90, 'death')

    # JHU
    util.redistribute(data['US']['data'], '2021-06-06', 85, 90, 'death')
    util.redistribute(data['CA']['data'], '2021-06-06', 85, 90, 'death')

    # JHU: Indiana 765 backlogged cases June 3
    util.redistribute(data['IN']['data'], '2021-06-03', 765, 90, 'confirmed')
    util.redistribute(data['US']['data'], '2021-06-03', 765, 90, 'confirmed')

    util.redistribute(data['WI']['data'], '2021-05-31', 16, 90, 'death')
    util.redistribute(data['WI']['data'], '2021-06-01',  9, 90, 'death')
    util.redistribute(data['WI']['data'], '2021-06-02',  9, 90, 'death')
    util.redistribute(data['WI']['data'], '2021-06-03', 20, 90, 'death')
    util.redistribute(data['WI']['data'], '2021-06-04', 21, 90, 'death')

    # https://www.penbaypilot.com/article/update-maine-s-covid-19-death-toll-rises-10/147794
    util.redistribute(data['ME']['data'], '2021-06-03', 7, 36, 'death')

    # https://www.kentucky.com/news/coronavirus/article251818393.html
    util.redistribute(data['KY']['data'], '2021-06-01', 260, 90, 'death')

    # https://twitter.com/Delaware_DHSS
    util.redistribute(data['DE']['data'], '2021-06-02', 3, 90, 'death')
    util.redistribute(data['DE']['data'], '2021-06-03', 2, 90, 'death')
    util.redistribute(data['DE']['data'], '2021-06-04', 5, 90, 'death')
    util.redistribute(data['DE']['data'], '2021-06-05', 3, 90, 'death')

    util.redistribute(data['WI']['data'], '2021-05-27', 39, 90, 'death')

    # https://github.com/CSSEGISandData/COVID-19/issues/4147
    util.redistribute(data['CA']['data'], '2021-05-27', 3857, 90, 'confirmed')
    util.redistribute(data['US']['data'], '2021-05-27', 3857, 90, 'confirmed')

    # JHU / https://southernmarylandchronicle.com/2021/05/27/maryland-department-of-health-vital-statistics-administration-issues-revision-of-covid-19-death-data/
    util.redistribute(data['MD']['data'], '2021-05-27', 517+21, 90, 'death')
    util.redistribute(data['US']['data'], '2021-05-27', 517+21, 90, 'death')

    # JHU

    # JHU / https://www.kob.com/new-mexico-news/new-mexico-to-add-approximately-100-more-covid-19-deaths-to-states-total/6117386/
    util.redistribute(data['NM']['data'], '2021-05-24', 110, 90, 'death')

    # https://www.wmtw.com/article/maine-coronavirus-covid19-cases-deaths-update-may-20/36487747
    util.redistribute(data['ME']['data'], '2021-05-20', 8, 90, 'death')

    # https://www.nytimes.com/interactive/2021/us/delaware-covid-cases.html
    util.redistribute(data['DE']['data'], '2021-05-19', 653, 90, 'confirmed')

    # https://content.govdelivery.com/accounts/AKDHSS/bulletins/2d9a43d
    util.redistribute(data['AK']['data'], '2021-05-17', 10, 90, 'death')

    # JHU report
    util.redistribute(data['MO']['data'], '2021-05-18', 113, 90, 'death')

    # JHU Alabama reported large numbers of backlogged cases on both 5/13 (306) and 5/14 (2964). 
    # More details, including quotes from the source, are available on our GitHub repository:
    # https://github.com/CSSEGISandData/COVID-19/issues/4087 
    util.redistribute(data['AL']['data'], '2021-05-13', 306, 90, 'confirmed')
    util.redistribute(data['AL']['data'], '2021-05-14', 2964, 90, 'confirmed')
    util.redistribute(data['AL']['data'], '2021-05-14', 1500, 90, 'confirmed')
    util.redistribute(data['AL']['data'], '2021-05-15', 1500, 90, 'confirmed')

    util.redistribute(data['CO']['data'], '2021-05-12', 20, 90, 'death')
    
    # weirdness
    util.redistribute(data['NE']['data'], '2021-05-12', 10, -10, 'death')
    util.redistribute(data['NE']['data'], '2021-05-13', 29, -9, 'death')
    util.redistribute(data['NE']['data'], '2021-05-21', 12, 5, 'death')

    # JHU weekly report
    util.redistribute(data['NJ']['data'], '2021-05-05', 1295-98, 90, 'confirmed')

    util.redistribute(data['IA']['data'], '2021-05-06', 15, 5, 'death')

    # OK 5-26 spike
    util.redistribute(data['OK']['data'], '2021-05-26', 333, 90, 'death')
    util.redistribute(data['US']['data'], '2021-05-26', 333, 90, 'death')

    # OK 4-7 spike
    util.redistribute(data['OK']['data'], '2021-04-07', (1716-103), 300, 'death') # big spike on 04-07: JHU
    util.redistribute(data['US']['data'], '2021-04-07', (1716-103), 300, 'death') # also at US level
    util.redistribute(data['OK']['data'], '2021-04-07', 1300, 300, 'confirmed') # case spike OK
    util.redistribute(data['US']['data'], '2021-04-07', 1300, 300, 'confirmed') # case spike US

    # possible weird effects of weekend cycle
    util.redistribute(data['NM']['data'], '2021-04-05', 443*2//3, 2, 'confirmed')
    util.redistribute(data['NM']['data'], '2021-04-12', 619*2//3, 2, 'confirmed')
    util.redistribute(data['NM']['data'], '2021-04-19', 610*2//3, 2, 'confirmed')
    util.redistribute(data['NM']['data'], '2021-04-26', 623*2//3, 2, 'confirmed')

    # fix huge neg. number
    util.redistribute(data['NJ']['data'], '2021-04-26', -10800, 90, 'confirmed')

    # JHU weekly report
    util.redistribute(data['WV']['data'], '2021-04-27', -162, 90, 'death')

    # https://content.govdelivery.com/accounts/AKDHSS/bulletins/2d226f2?reqfrom=share
    # Twelve deaths of Alaska residents over the past several months were identified through death certificate review:
    util.redistribute(data['AK']['data'], '2021-04-26', 12, 90, 'death')

    util.redistribute(data['IA']['data'], '2021-04-30', 16, 5, 'death')

    # fix weird jump then drop on 4-30 and 5-01 (fixed in JHU data as of May 09)
    # util.redistribute(data['CA']['data'], '2021-05-01', -312, 1, 'death')

    # https://www.nytimes.com/interactive/2021/us/tennessee-covid-cases.html
    util.redistribute(data['TN']['data'], '2021-04-19', 2000, 90, 'confirmed')
    util.redistribute(data['MA']['data'], '2021-04-22', 800,  90, 'confirmed')

    # JHU weekly report
    util.redistribute(data['AL']['data'], '2021-04-20', 1110, 90, 'confirmed')

    util.redistribute(data['IA']['data'], '2021-04-24', 17, 14, 'death')

    util.redistribute(data['MA']['data'], '2021-04-04', -1000, -6, 'confirmed')
    #util.redistribute(data['MA']['data'], '2021-04-04', -1000,  6, 'confirmed')

    # https://chfs.ky.gov/Pages/cvdaily.aspx?View=April%202021%20Daily%20Summaries&Title=Table%20Viewer%20Webpart
    util.redistribute(data['KY']['data'], '2021-04-23', 17, 90, 'death')
    util.redistribute(data['KY']['data'], '2021-04-24', 11, 90, 'death')

    # https://www.wthr.com/article/news/health/latest-indiana-coronavirus-updates-global-death-toll-tops-3-million-saturday-april-17-speedway-clinic/531-c41b3be8-59f0-468c-a4f7-63b7dbe00b4e
    util.redistribute(data['IN']['data'], '2021-04-17', 1241, 90, 'confirmed')

    # JHU weekly report
    util.redistribute(data['AL']['data'], '2021-04-13', 1150, 90, 'confirmed')
    
    # JHU / https://siouxlandnews.com/news/coronavirus/covid-19-in-nebraska-04-15-2021
    util.redistribute(data['NE']['data'], '2021-04-15', -22, 90, 'death')
    
    # https://github.com/CSSEGISandData/COVID-19/issues/3975
    # reported drop of 11454 doesn't seem plausible --- add 2200
    util.redistribute(data['MO']['data'], '2021-04-17', -11454+2200, 300, 'confirmed')

    # JHU weekly report
    util.redistribute(data['AK']['data'], '2021-04-15', 20, 90, 'death')

    # https://www.8newsnow.com/news/health/coronavirus-health/new-covid-19-cases-highest-in-a-month-18-fully-vaccinated/
    # https://www.8newsnow.com/news/health/coronavirus-health/new-nevada-clark-county-report-high-covid-19-case-counts-for-2nd-consecutive-day-due-to-delayed-electronic-laboratory-reports/
    util.redistribute(data['NV']['data'], '2021-04-10', 164, 90, 'confirmed')
    util.redistribute(data['NV']['data'], '2021-04-10', 471, 90, 'confirmed')

    # Guessing
    util.redistribute(data['NE']['data'], '2021-04-08', 21, 30, 'death')
    util.redistribute(data['NE']['data'], '2021-04-09', 9, 20, 'death')

    # JHU / Billings Gazette (e.g., https://billingsgazette.com/news/state-and-regional/montana-reports-218-covid-19-cases-11-deaths/article_54c208c7-c57e-5dc2-9d97-9eb8251dd949.html)
    util.redistribute(data['MT']['data'], '2021-04-06', 11, 90, 'death')
    util.redistribute(data['MT']['data'], '2021-04-07', 9, 90, 'death')
    util.redistribute(data['MT']['data'], '2021-04-09', 72, 90, 'confirmed')
    util.redistribute(data['MT']['data'], '2021-04-09', 26, 90, 'death')

    util.redistribute(data['MT']['data'], '2021-04-02', 13, 21, 'death')    
    util.redistribute(data['MT']['data'], '2021-04-03', 8, 7, 'death')    

    # Guessing
    util.redistribute(data['NE']['data'], '2021-04-02', 600, 30, 'confirmed')

    # https://www.wabi.tv/2021/04/02/401-newly-recorded-coronavirus-cases-in-maine-highest-one-day-increase-in-more-than-two-months/
    util.redistribute(data['ME']['data'], '2021-04-02', 150, 4, 'confirmed')

    # https://dhhr.wv.gov/News/2021/Pages/COVID-19-Daily-Update-3-31-2021.aspx
    util.redistribute(data['WV']['data'], '2021-03-31', 34, 90, 'death')    

    # https://who13.com/news/coronavirus/iowa-reports-68-more-covid-19-deaths-and-431-new-cases/
    # mentions backdatings, nonspecific
    util.redistribute(data['IA']['data'], '2021-04-03', 65, 90, 'death')

    # JHU: 2,029 historical cases; Ellis County reported 294
    util.redistribute(data['TX']['data'], '2021-03-26', 2029+294, 90, 'confirmed')

    util.redistribute(data['MN']['data'], '2021-03-25', 20, 20, 'death')
    util.redistribute(data['VI']['data'], '2021-03-24', 100, 14, 'confirmed')
    util.redistribute(data['NE']['data'], '2021-03-24', 25, 20, 'death')

    # https://github.com/CSSEGISandData/COVID-19/issues/3869
    util.redistribute(data['NY']['data'], '2021-03-24', 15000, 3, 'confirmed')
    util.redistribute(data['NY']['data'], '2021-03-24', 3*255//4, 3, 'death')
    util.redistribute(data['NY']['data'], '2021-03-24', 4000, 30, 'confirmed') # guess

    # https://covid19.ncdhhs.gov/dashboard
    util.redistribute(data['NC']['data'], '2021-03-25', 68, 90, 'death')

    #  e.g. https://chfs.ky.gov/cvdaily/COVID19DailyReport032521.pdf
    util.redistribute(data['KY']['data'], '2021-03-22', 50, 90, 'death')
    util.redistribute(data['KY']['data'], '2021-03-23', 4, 90, 'death')
    util.redistribute(data['KY']['data'], '2021-03-24', 25, 90, 'death')
    util.redistribute(data['KY']['data'], '2021-03-25', 88, 90, 'death')
    util.redistribute(data['KY']['data'], '2021-03-26', 11, 90, 'death')

    util.redistribute(data['CA']['data'], '2021-03-25', 200, 90, 'death')

    # https://dhhr.wv.gov/News/2021/Pages/COVID-19-Daily-Update-3-19-2021.aspx
    util.redistribute(data['WV']['data'], '2021-03-19', 20, 90, 'death')

    # https://github.com/CSSEGISandData/COVID-19/issues/3826
    util.redistribute(data['AL']['data'], '2021-03-15', 4007, 90, 'confirmed')

    # JHU
    util.redistribute(data['KY']['data'], '2021-03-18', 417, 90, 'death')
    util.redistribute(data['KY']['data'], '2021-03-19', 166, 90, 'death')

    util.redistribute(data['CA']['data'], '2021-03-13', 600, 90, 'death')

    # https://www.wabi.tv/2021/03/09/17-new-covid-related-deaths-in-maine-139-new-cases/
    util.redistribute(data['ME']['data'], '2021-03-09', 17, 45, 'death')

    # JHU: 891 backlogged cases and 138 backlogged deaths reported on March 9
    util.redistribute(data['MN']['data'], '2021-03-09', 891, 90, 'confirmed')
    util.redistribute(data['MN']['data'], '2021-03-09', 138, 90, 'death')

    # JHU: West Virginia published 165 backlogged deaths on March 12
    util.redistribute(data['WV']['data'], '2021-03-12', 165, 90, 'death')

    # JHU weekly update
    util.redistribute(data['TX']['data'], '2021-03-03', 1614, 90, 'confirmed')

    # JHU: Alaska backlogged deaths: Nine backlogged deaths on March 1 
    util.redistribute(data['AK']['data'], '2021-03-01', 9, 60, 'death')

    # JHU weekly update
    util.redistribute(data['AL']['data'], '2021-03-03', 2114, 90, 'confirmed')

    # JHU
    util.redistribute(data['PR']['data'], '2021-02-21', 15, 90, 'death')
    util.redistribute(data['PR']['data'], '2021-02-24', 15, 90, 'death')

    # JHU
    util.redistribute(data['WI']['data'], '2021-02-25', 30, 10, 'death')

    # https://twitter.com/ADHPIO/status/1366163333225799682
    util.redistribute(data['AR']['data'], '2021-02-28', 2932, 90, 'confirmed')
    util.redistribute(data['AR']['data'], '2021-02-28', -174, 90, 'death')

    # "Virginia daily reports include many backlogged deaths and this behavior is anticipated to continue." -JHU
    util.redistribute(data['VA']['data'], '2021-02-20', 74, 90, 'death')
    util.redistribute(data['VA']['data'], '2021-02-21', 109, 90, 'death')
    util.redistribute(data['VA']['data'], '2021-02-22', 130, 90, 'death')
    util.redistribute(data['VA']['data'], '2021-02-23', 147, 90, 'death')
    util.redistribute(data['VA']['data'], '2021-02-24', 124, 90, 'death')
    util.redistribute(data['VA']['data'], '2021-02-25', 131, 90, 'death')
    util.redistribute(data['VA']['data'], '2021-02-26', 209, 90, 'death')
    util.redistribute(data['VA']['data'], '2021-02-27', 160, 90, 'death')    
    util.redistribute(data['VA']['data'], '2021-02-28', 140, 90, 'death')
    util.redistribute(data['VA']['data'], '2021-03-01', 200, 90, 'death')
    util.redistribute(data['VA']['data'], '2021-03-02', 125, 90, 'death')
    util.redistribute(data['VA']['data'], '2021-03-03', 350, 90, 'death')    
    util.redistribute(data['VA']['data'], '2021-03-04', 0, 90, 'death')    
    util.redistribute(data['VA']['data'], '2021-03-05', 40, 90, 'death')    
    util.redistribute(data['VA']['data'], '2021-03-06', 50, 90, 'death')    
    util.redistribute(data['VA']['data'], '2021-03-07', 47, 90, 'death')
    util.redistribute(data['VA']['data'], '2021-03-08', 57, 90, 'death')
    util.redistribute(data['VA']['data'], '2021-03-09', 77, 90, 'death')
    util.redistribute(data['VA']['data'], '2021-03-10', 29, 90, 'death')
    util.redistribute(data['VA']['data'], '2021-03-11', 23, 90, 'death')
    util.redistribute(data['VA']['data'], '2021-03-12', 29, 90, 'death')
    util.redistribute(data['VA']['data'], '2021-03-19', -100, 30, 'death')


    # JHU CSSE email: "39 historical deaths in Maine on February 23 and 24"
    util.redistribute(data['ME']['data'], '2021-02-24', 16, 90, 'death')
    util.redistribute(data['ME']['data'], '2021-02-25', 23, 90, 'death')

    # https://twitter.com/Delaware_DHSS
    # state reports 193 new cases; data says 789. redistribute difference
    util.redistribute(data['DE']['data'], '2021-03-11', 789-193, 90, 'confirmed')

    # https://twitter.com/Delaware_DHSS
    util.redistribute(data['DE']['data'], '2021-02-23', 8, 90, 'death')
    util.redistribute(data['DE']['data'], '2021-02-24', 18, 90, 'death')
    util.redistribute(data['DE']['data'], '2021-02-26', 9, 90, 'death')
    util.redistribute(data['DE']['data'], '2021-03-03', 11, 90, 'death')
    util.redistribute(data['DE']['data'], '2021-03-04', 4, 90, 'death')
    util.redistribute(data['DE']['data'], '2021-03-05', 9, 90, 'death')
    util.redistribute(data['DE']['data'], '2021-03-06', 8, 90, 'death')
    util.redistribute(data['DE']['data'], '2021-03-07', 6, 90, 'death')
    util.redistribute(data['DE']['data'], '2021-03-08', 2, 90, 'death')
    util.redistribute(data['DE']['data'], '2021-03-10', 8, 90, 'death')
    util.redistribute(data['DE']['data'], '2021-03-13', 5, 90, 'death')

    util.redistribute(data['MP']['data'], '2021-02-20', 7, 7, 'confirmed')

    # https://github.com/CSSEGISandData/COVID-19/issues/3705
    # (backdistributed week of March 1)
    #util.redistribute(data['IA']['data'], '2021-02-19', 26775, 200, 'confirmed')
    

    # https://covidtracking.com/data/state/ohio/notes
    #util.redistribute(data['OH']['data'], '2021-02-11', 650, 90, 'death')
    #util.redistribute(data['OH']['data'], '2021-02-12', 2500, 90, 'death')
    #util.redistribute(data['OH']['data'], '2021-02-13', 1125, 90, 'death')

    # https://content.govdelivery.com/accounts/AKDHSS/bulletins/2be6de2
    # "All 17 deaths were identified through death certificate review"
    util.redistribute(data['AK']['data'], '2021-02-02', 17, 60, 'death')

    # https://twitter.com/Delaware_DHSS/status/1357838111879921671
    #util.redistribute(data['DE']['data'], '2021-02-05', 54, 90, 'death')
    # https://twitter.com/Delaware_DHSS/status/1357060070538940420
    #util.redistribute(data['DE']['data'], '2021-02-03', 17, 30, 'death')

    # See JHU github
    util.redistribute(data['IN']['data'], '2021-02-04', 150, 90, 'death')

    # https://www.kwch.com/2021/02/05/1st-child-death-from-covid-19-reported-in-kansas/
    # A KDHE spokesperson said that the department was reviewing death 
    # certificates, which contributes to the increase in deaths.
    #util.redistribute(data['KS']['data'], '2021-02-02', 150, 60, 'death')

    # can't find a specific record
    util.redistribute(data['MT']['data'], '2021-02-03', 25, 60, 'death')


    # No details released, but pretty sure these are older deaths
    # https://www.kcrg.com/2021/01/31/reported-covid-19-deaths-in-iowa-swell-to-over-4900/
    util.redistribute(data['IA']['data'], '2021-01-31', 240, 60, 'death')
    util.redistribute(data['IA']['data'], '2021-01-30', 30, 60, 'death')

    # https://twitter.com/scdhec/status/1354893314777088008
    util.redistribute(data['SC']['data'], '2021-01-27', 54, 30, 'death')
    util.redistribute(data['SC']['data'], '2021-01-28', 200, 30, 'death')

    # https://health.hawaii.gov/news/covid-19/hawaii-covid-19-daily-news-digest-january-26-2021/
    util.redistribute(data['HI']['data'], '2021-01-26', 59, 90, 'death')


    util.redistribute(data['MT']['data'], '2021-01-23', 30, 60, 'death')

    # https://content.govdelivery.com/accounts/AKDHSS/bulletins/2bb208d
    util.redistribute(data['AK']['data'], '2021-01-23', 5, 60, 'death')

    # https://content.govdelivery.com/accounts/AKDHSS/bulletins/2ba597a
    util.redistribute(data['AK']['data'], '2021-01-20', 22, 60, 'death')


    util.redistribute(data['WI']['data'], '2021-01-16', 60, 20, 'death')

    # Rebalance large pos/neg vaules Jan 7/8
    util.redistribute(data['NE']['data'], '2021-01-08', -90, 1, 'death')

    # 23 of the deaths reported on the 16th were from between Dec 24 and Jan 16
    # https://www.pressherald.com/2021/01/16/maine-cdc-reports-30-deaths-444-new-cases-of-covid-19/
    util.redistribute(data['ME']['data'], '2021-01-16', 23, 24, 'death')

    # 35 of the deaths reported on Jan 8 were from December. 
    # https://www.wabi.tv/2021/01/08/maine-sees-deadliest-day-of-pandemic-with-41-deaths-789-new-cases/
    util.redistribute(data['ME']['data'], '2021-01-08', 35, 40, 'death')


    # The WA saga....
    util.redistribute(data['WA']['data'], '2021-02-08', 20, 60, 'death')
    util.redistribute(data['WA']['data'], '2021-02-09', 20, 60, 'death')
    util.redistribute(data['WA']['data'], '2021-02-10', 10, 60, 'death')
    util.redistribute(data['WA']['data'], '2021-02-12', 10, 60, 'death')

    # and again!
    util.redistribute(data['WA']['data'], '2021-01-22', 20, 6, 'death')
    util.redistribute(data['WA']['data'], '2021-01-21', 100, 5, 'death')
    util.redistribute(data['WA']['data'], '2021-01-19', 25, 3, 'death')

    # WA weirdness seems to be weekly....
    util.redistribute(data['WA']['data'], '2021-01-12', 60, 3, 'death')
    util.redistribute(data['WA']['data'], '2021-01-13', 20, 4, 'death')

    # More WA cleanup after New Year's. Sigh.
    # Used time series download from WA dashboard as reference, but could not
    # make numbers match closely. Dashboard reports ~20 or fewer deaths each
    # day since start of Jan
    util.redistribute(data['WA']['data'], '2021-01-03', 5000, 2, 'confirmed')
    util.redistribute(data['WA']['data'], '2021-01-08', 30, 30, 'death')
    util.redistribute(data['WA']['data'], '2021-01-08', 10, 7, 'death')
    util.redistribute(data['WA']['data'], '2021-01-07', 10, 30, 'death')
    util.redistribute(data['WA']['data'], '2021-01-06', 30, 30, 'death')
    util.redistribute(data['WA']['data'], '2021-01-06', 10, 5, 'death')
    util.redistribute(data['WA']['data'], '2021-01-05', 25, 30, 'death')
    util.redistribute(data['WA']['data'], '2021-01-05', 10, 4, 'death')
    util.redistribute(data['WA']['data'], '2021-01-04', 15, 3, 'death')


    # Manual smoothing due to combined lack of reporting after Christmas and 
    # imprecise report that a backlog of "approximately 200 deaths" were 
    # reported ~12-29. 
    # https://covid-tracking-project-data.s3.us-east-1.amazonaws.com/state_screenshots/WA/WA-20201230-001452.png
    util.redistribute(data['WA']['data'], '2020-12-29', 120, 60, 'death')
    util.redistribute(data['WA']['data'], '2020-12-29', 40, 4, 'death')
    util.redistribute(data['WA']['data'], '2020-12-30', 20, 60, 'death')
    util.redistribute(data['WA']['data'], '2020-12-31', 20, 60, 'death')


    # 2020-12-20
    # manual smoothing of WA after data update left things very wonky
    util.redistribute(data['WA']['data'], '2020-12-16', -1600, -3, 'confirmed')
    util.redistribute(data['WA']['data'], '2020-12-16', 80, 7, 'death')
    util.redistribute(data['WA']['data'], '2020-12-17', 25, 7, 'death')
    util.redistribute(data['WA']['data'], '2020-12-17', 20, -1, 'death')
    util.redistribute(data['WA']['data'], '2020-12-17', 20, -2, 'death')

    # 2020-12-20
    # California dashboard included 15,337 historical cases in their December 16 update
    # https://github.com/CSSEGISandData/COVID-19/tree/master/csse_covid_19_data
    util.redistribute(data['CA']['data'], '2020-12-16', 15337, 60, 'confirmed')


    # 2020-12-07: manual smoothing of MA/ME data on Thanksgiving and following
    util.redistribute(data['MA']['data'], '2020-11-26', -3000, -7, 'confirmed')
    util.redistribute(data['MA']['data'], '2020-11-27', 500, 1, 'confirmed')
    util.redistribute(data['MA']['data'], '2020-11-30', -1500, -6, 'confirmed')
    util.redistribute(data['MA']['data'], '2020-12-03', 1500, 7, 'confirmed')

    util.redistribute(data['ME']['data'], '2020-11-27', -200, -7, 'confirmed')
    util.redistribute(data['ME']['data'], '2020-11-28', -200, -7, 'confirmed')
    util.redistribute(data['ME']['data'], '2020-12-03', 60, 7, 'confirmed')
    

    # 1922 antigen tests first reported on Dec 9th. 
    # https://www.health.nd.gov/news/positive-covid-19-test-results-249
    util.redistribute(data['ND']['data'], '2020-12-09', 1922, 60, 'confirmed')

    # Iowa deaths messed up due to change in reporting. Pieced together
    # by using Covid Tracking and news reports
    #
    # https://twitter.com/natalie_krebs?lang=en
    # https://www.iowapublicradio.org/health/2020-12-08/iowa-officials-announce-change-in-methodology-that-raises-covid-19-death-count-by-175
    data['IA']['data'].loc['2020-12-7':'2020-12-12','death'] = [2919, 3021, 3120, 3197, 3212, 3213]
    util.redistribute(data['IA']['data'], '2020-12-07', 175, 60, 'death')

    # AL antigen backlogs in December
    # (https://alpublichealth.maps.arcgis.com/apps/opsdashboard/index.html#/6d2771faa9da4a2786a509d82c8cf0f7)
    util.redistribute(data['AL']['data'], '2020-12-02', 706, 60, 'confirmed')
    util.redistribute(data['AL']['data'], '2020-12-08', 1038 + 473, 60, 'confirmed')
    util.redistribute(data['AL']['data'], '2020-12-10', 473, 60, 'confirmed')
    util.redistribute(data['AL']['data'], '2020-12-12', 398, 60, 'confirmed')

    #  13000 case backlog (JHU CSSE)
    util.redistribute(data['OH']['data'], '2020-12-08', 13000, 60, 'confirmed')

    # JHU redistribution error for WI
    util.redistribute(data['WI']['data'], '2020-10-19', 11000, 3, 'confirmed')

    # GA backlog on Nov 3 (JHU CSSE)
    util.redistribute(data['GA']['data'], '2020-11-03', 29937, 60, 'confirmed')
    util.redistribute(data['GA']['data'], '2020-11-03', 450, 60, 'death')


    # Backlogs from LA county on 10/22, 10/23, 10/24
    #  - https://twitter.com/lapublichealth
    util.redistribute(data['CA']['data'], '2020-10-22', 2000, 60, 'confirmed')
    util.redistribute(data['CA']['data'], '2020-10-23', 2000, 60, 'confirmed')
    util.redistribute(data['CA']['data'], '2020-10-24', 1200, 60, 'confirmed')

    # AL backlogs of cases on 10/23 and 10/24
    #  https://github.com/CSSEGISandData/COVID-19/issues/3264
    #  - 2565 on 10/22 (appar in JHU on 10/23) - from June through Oct 18
    #  - "majority of" 1182 on 10/23 (appear in JHU on 10/24) - from April through Sep
    #    util.redistribute(data['AL']['data'], '2020-10-23', 2565, 100, 'confirmed')
    #    util.redistribute(data['AL']['data'], '2020-10-24', 1182, 100, 'confirmed')


    # NH: 129 old cases on 2020-10-02 
    # https://www.nh.gov/covid19/news/documents/covid-19-update-10022020.pdf
    # util.redistribute(data['NH']['data'], '2020-10-02', 139, 90, 'confirmed')
    # #   some gaps in JHU filled with covidtracking
    # data['NH']['data'].loc['2020-09-17', 'confirmed'] = 7814
    # data['NH']['data'].loc['2020-10-05', 'confirmed'] = 8680
    # data['NH']['data'].loc['2020-10-07', 'confirmed'] = 8800

    # MO dept. of health and human services reports 129 excess deaths
    # added to the system ~Mon-Wed 9/21-9/23 and 63 added on 9/26.
    # These jumps don't seem to match what appears in JHU data, so
    # I am redistributing a similar (slightly smaller) number 
    # of deaths from multiple days during the week
    # https://twitter.com/HealthyLivingMo
    #
    # More wonky stuff on 10-02 and 10-03. New dashboard has 3 day delay
    # before showing official numbers so *very* hard to tell what should
    # be correct. Given that official MO dashboard shows deaths in single
    # digits most of past 7 days I am assuming the JHU data is due to
    # backlogs or errors
    # 
    # UPDATE: MO deaths is a complete mess. They seem to report backlogs
    # ~once/week. What is below now amounts to just an attempt at smoothing.
    # util.redistribute(data['MO']['data'], '2020-09-22', 20, 30, 'death')
    # util.redistribute(data['MO']['data'], '2020-09-23', 65, 30, 'death')
    # util.redistribute(data['MO']['data'], '2020-09-25', 30, 30, 'death')
    # util.redistribute(data['MO']['data'], '2020-09-26', 55, 30, 'death')
    # util.redistribute(data['MO']['data'], '2020-09-27', -4, 30, 'death')
    # util.redistribute(data['MO']['data'], '2020-10-02', 60, 30, 'death')
    # util.redistribute(data['MO']['data'], '2020-10-03', 20, 30, 'death')
    # util.redistribute(data['MO']['data'], '2020-10-09', 100, 30, 'death')
    # util.redistribute(data['MO']['data'], '2020-10-15', -100, 2, 'death')
    # util.redistribute(data['MO']['data'], '2020-10-17', 100, 30, 'death')
    # util.redistribute(data['MO']['data'], '2020-10-24', 90, 30, 'death')


    # Texas large backlogs on 9/21 and 9/22

    # 9/21 - 2,078 older case recently reported by labs were included
    #        in the statewide total but excluded from statewide and
    #        Bexar County new confirmed cases (103).  3 older cases
    #        recently reported by labs were included in the statewide
    #        total but excluded from statewide and Collin County new
    #        confirmed cases (42).  306 older case recently reported
    #        by labs were included in the statewide total but excluded
    #        from statewide and Dallas County new confirmed cases
    #        (465).  298 older cases recently reported by labs were
    #        included in the statewide total but excluded from
    #        statewide and Frio County new confirmed cases (1).  328
    #        older cases recently reported by labs were included in
    #        the statewide total but excluded from statewide and
    #        Harris County new confirmed cases (225).  1 older case
    #        recently reported by labs was included in the statewide
    #        total but excluded from statewide and Houston County new
    #        confirmed cases (2).  125 older cases recently reported
    #        by labs were included in the statewide total but excluded
    #        from statewide and Tarrant County new confirmed cases
    #        (203).  Older cases are being reported for several
    #        counties in Public Health Region 8 after DSHS staff
    #        identified 3,921 cases that had not previously been
    #        reported. Those counties are Atascosa (522), Bandera
    #        (41), Calhoun (186), Dimmit (53), Edwards (33), Gillespie
    #        (96), Gonzales (234), Guadalupe (1587), Jackson (77),
    #        Karnes (181), Kendall (128), Kerr (142), Kinney (19),
    #        Lavaca (252), Real (12), Wilson (307) and Zavala
    #        (51). There are no new cases reported for those counties
    #        today.

    # 9/22 - 2 older cases recently reported by labs were included in
    # the statewide total but excluded from statewide and Dallas
    # County new confirmed cases (314).  13,622 older cases recently
    # reported by labs were included in the statewide total but
    # excluded from statewide and Harris County new confirmed cases
    # (507).  231 older cases recently reported by labs were included
    # in the statewide total but excluded from statewide and Nueces
    # County new confirmed cases (1).  1 older cases recently reported
    # by labs was included in the statewide total but excluded from
    # statewide and San Jacinto County new confirmed cases (0).

    # As nearly as I can tell the notes above apply to the previous day
    util.redistribute(data['TX']['data'], '2020-09-20', 2078 + 3 + 306 + 298 + 328 + 1 + 125, 90, 'confirmed')
    util.redistribute(data['TX']['data'], '2020-09-21', 13622 + 231 + 1, 90, 'confirmed')

    # 139 probable deaths added on Sep 15 https://katv.com/news/local/arkansas-gov-asa-hutchinson-to-give-covid-19-briefing-09-15-2020
    util.redistribute(data['AR']['data'], '2020-09-15', 139, 30, 'death')

    # 577 backlog cases on Sep 17 https://directorsblog.health.azdhs.gov/covid-19-antigen-tests/
    # 764 backlog cases on Sep 18 https://twitter.com/AZDHS
    util.redistribute(data['AZ']['data'], '2020-09-17', 577, 90, 'confirmed')
    util.redistribute(data['AZ']['data'], '2020-09-18', 764, 90, 'confirmed')

    # Correct values 9/15 through 9/20 are: 91,304 92,712 94,746 97,279 99,562 101,227 (source: https://www.dhs.wisconsin.gov/covid-19/cases.htm)
    # data['WI']['data'].loc['2020-09-15':'2020-09-20', 'confirmed'] = [91304, 92712, 94746, 97279, 99562, 101227]
