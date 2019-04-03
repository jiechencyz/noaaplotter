#!/usr/bin/python
# -*- coding: utf-8 -*-

########################
# Credits here
# author: Ingmar Nitze, Alfred Wegener Institute for Polar and Marine Research
# contact: ingmar.nitze@awi.de
# version: 2019-04-03

########################
import pandas as pd
from matplotlib import pyplot as plt
import datetime
import numpy as np

class NOAAPlotter(object):
    """
    This class/module creates nice plots of observed weather data from NOAA
    """
    def __init__(self,
                 input_filepath,
                 remove_feb29=False,
                 climate_start=pd.datetime(1981, 1, 1),
                 climate_end=pd.datetime(2010, 12, 31)):
        """

        :param input_filepath:
        :param remove_feb29:
        :param climate_start:
        :param climate_end:
        """
        self.input_filepath = input_filepath
        self.climate_start = climate_start
        self.climate_end = climate_end
        self.remove_feb29 = remove_feb29
        self.df_ = self._load_file()
        self._update_datatypes()
        self._get_datestring()
        self._get_tmean()
        self._remove_feb29()
        self.df_clim_ = self._filter_to_climate()
        self.df_clim_doy_ = self._get_daily_stats(self.df_clim_)

    def _load_file(self):
        """
        load csv file into Pandas DataFrame
        :return:
        """
        return pd.read_csv(self.input_filepath)

    def _update_datatypes(self):
        self.df_['DATE'] = pd.to_datetime(self.df_['DATE'])

    def _get_datestring(self):
        self.df_['DATE_MD'] = self.df_.apply(lambda x: x['DATE'].strftime('%m-%d'), axis=1)

    def _get_tmean(self):
        """
        calculate mean daily temperature from min and max
        :return:
        """
        self.df_['TMEAN'] = self.df_[['TMIN', 'TMAX']].mean(axis=1)

    def _remove_feb29(self):
        """

        :return:
        """
        if self.remove_feb29:
            self.df_ = self.df_[~self.df_['DATE_MD'] != '02-29']

    def _filter_to_climate(self):
        """
        :return:
        """
        df_clim = self.df_[(self.df_['DATE'] >= self.climate_start) & (self.df_['DATE'] <= self.climate_end)]
        df_clim = df_clim[df_clim['DATE'].apply(lambda x: x.dayofyear != 366)]
        return df_clim

    @staticmethod
    def _get_daily_stats(df):
        """

        :param df:
        :return:
        """
        df_out = pd.DataFrame()
        df_out['tmean_doy_mean'] = df[['DATE', 'TMEAN']].groupby(df.DATE.dt.dayofyear).mean().TMEAN
        df_out['tmean_doy_std'] = df[['DATE', 'TMEAN']].groupby(df.DATE.dt.dayofyear).std().TMEAN
        df_out['tmax_doy_max'] = df[['DATE', 'TMAX']].groupby(df.DATE.dt.dayofyear).max().TMAX
        df_out['tmax_doy_std'] = df[['DATE', 'TMAX']].groupby(df.DATE.dt.dayofyear).std().TMAX
        df_out['tmin_doy_min'] = df[['DATE', 'TMIN']].groupby(df.DATE.dt.dayofyear).min().TMIN
        df_out['tmin_doy_std'] = df[['DATE', 'TMIN']].groupby(df.DATE.dt.dayofyear).std().TMIN
        df_out['snow_doy_mean'] = df[['DATE', 'SNOW']].groupby(df.DATE.dt.dayofyear).mean().SNOW
        return df_out
    @staticmethod
    def _parse_dates(date):
        if isinstance(date, str):
            return pd.datetime.strptime(date, '%Y-%m-%d')
        elif isinstance(date, pd.datetime):
            return date
        else:
            raise('Wrong date format. Either use native datetime format or "YYYY-mm-dd"')

    def plot_weather_series(self, start_date, end_date, plot_tmax=22, plot_tmin=-45):
        """
        Plotting Function to show observed vs climate temperatures and snowfall
        """
        # make dynamic end date within the function
        start_date = self._parse_dates(start_date)
        end_date = self._parse_dates(end_date)

        if self.df_.DATE.max() >= end_date:
            x_dates_short = pd.date_range(start=start_date, end=end_date)
        else:
            x_dates_short = pd.date_range(start=start_date, end=self.df_.DATE.max())
        x_dates = pd.date_range(start=start_date, end=end_date)

        df_obs = self.df_[(self.df_.DATE >= start_date) & (self.df_.DATE <= end_date)]
        df_obs = df_obs.set_index(df_obs.DATE.dt.dayofyear.values)

        clim_locs = x_dates.dayofyear[:365] # full year series
        clim_locs_short = x_dates_short.dayofyear # short series for incomplete years (actual data)

        # get mean and mean+-standard deviation of daily mean temperatures of climate series
        y_clim = self.df_clim_doy_.loc[clim_locs].tmean_doy_mean
        y_clim_short = self.df_clim_doy_.loc[clim_locs_short].tmean_doy_mean
        y_clim_std_hi = self.df_clim_doy_.loc[clim_locs][['tmean_doy_mean', 'tmean_doy_std']].sum(axis=1)
        y_clim_std_lo = self.df_clim_doy_.loc[clim_locs].apply(lambda x: x['tmean_doy_mean'] - x['tmean_doy_std'], axis=1)

        # Prepare data for filled plot areas
        t_above = np.vstack([df_obs.TMEAN.values, y_clim.loc[clim_locs_short].values]).max(axis=0)
        t_above_std = np.vstack([df_obs.TMEAN.values, y_clim_std_hi.loc[clim_locs_short].values]).max(axis=0)
        t_below = np.vstack([df_obs.TMEAN.values, y_clim.loc[clim_locs_short].values]).min(axis=0)
        t_below_std = np.vstack([df_obs.TMEAN.values, y_clim_std_lo.loc[clim_locs_short].values]).min(axis=0)

        # Calculate the date of last snowfall and cumulative sum of snowfall
        last_snow = np.where(df_obs.SNOW > 0)[0][-1]
        snow_acc = np.cumsum(df_obs.SNOW)

        #PLOT
        fig = plt.figure(figsize=(15,10))
        ax = fig.add_subplot(211)
        ax2 = fig.add_subplot(212, sharex=ax)
        ax2_snow = ax2.twinx()

        # climate series (red line)
        cm, = ax.plot(x_dates, y_clim, c='k', alpha=0.5, lw=2)
        cm_hi, = ax.plot(x_dates, y_clim_std_hi, c='r', ls='--', alpha=0.4, lw=1)
        cm_low, = ax.plot(x_dates, y_clim_std_lo, c='r', ls='--', alpha=0.4, lw=1)

        # observed series (grey line)
        fb, = ax.plot(x_dates_short, df_obs.TMEAN, c='k', alpha=0.4, lw=1.2)

        # difference of observed and climate (grey area)
        fill_r = ax.fill_between(x_dates_short, y1=t_above, y2=y_clim.loc[clim_locs_short], facecolor='#d6604d', alpha=0.5)
        fill_rr = ax.fill_between(x_dates_short, y1=t_above_std, y2=y_clim_std_hi.loc[clim_locs_short], facecolor='#d6604d', alpha=0.7)
        fill_b = ax.fill_between(x_dates_short, y1=y_clim.loc[clim_locs_short], y2=t_below, facecolor='#4393c3', alpha=0.5)
        fill_bb = ax.fill_between(x_dates_short, y1=y_clim_std_lo.loc[clim_locs_short], y2=t_below_std, facecolor='#4393c3', alpha=0.7)

        xlim = ax.get_xlim()
        ax.hlines(0, *xlim, linestyles='--')
        # grid
        ax.grid()

        # labels
        ax.set_xlim(x_dates[0], x_dates[-1])
        ax.set_ylim(plot_tmin, plot_tmax)
        ax.set_ylabel('t in °C')
        ax.set_xlabel('Date')
        ax.set_title('Observed temperatures {s}/{e} vs. climatological mean (1981-2010)'.format(s=start_date.year, e=end_date.year))

        # add legend
        ax.legend([fb, cm, cm_hi, fill_r, fill_b], ['Observed Temperatures',
                                                 'Climatological Mean',
                                                    'Std of Climatological Mean',
                                                 'Above average Temperature',
                                                'Below average Temperature'], loc='lower left')

        #PRECIPITATION#
        rain = ax2.bar(x=x_dates_short, height=df_obs.PRCP, fc='b', alpha=0.6)
        sn_acc = ax2_snow.fill_between(x=x_dates_short[:last_snow], y1=snow_acc[:last_snow]/10, facecolor='k', alpha=0.2)
        _ = ax2_snow.plot(x_dates_short[last_snow-1:], snow_acc[last_snow-1:]/10, c='k', alpha=0.2, ls='--')
        # grid
        ax2.grid()
        # labels
        ax2.set_ylabel('Precipitation in mm')
        ax2.set_xlabel('Date')
        ax2_snow.set_ylabel('Accumulated Snowfall in cm')
        ax2.legend([rain, sn_acc], ['Precipitation',
                                  'Accumulated Snowfall'], loc='upper left')
        ax2.set_ylim(0, 30)
        ax2_snow.set_ylim(0, 300)

        ax2.set_title('Precipitation pattern {s}/{e}'.format(s=start_date.year, e=end_date.year))

        plt.show()
        print("Freezing Degrees:", df_obs[df_obs.TMEAN < 0].TMEAN.sum())
        print("Freezing Days:", df_obs[df_obs.TMEAN < 0].TMEAN.count())
        print('Days with T above 1 std:', (df_obs.loc[clim_locs, 'TMEAN'] > y_clim_std_hi.loc[clim_locs]).sum())
        print('Days with T below 1 std:', (df_obs.loc[clim_locs, 'TMEAN'] < y_clim_std_lo.loc[clim_locs]).sum())

        print("\n\n\n")