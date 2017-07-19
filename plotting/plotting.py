#!/usr/bin/env python

# Copyright (C) 2017 Andy Aschwanden

from argparse import ArgumentParser
import matplotlib.transforms as transforms
from netCDF4 import Dataset as NC
import numpy as np
import pylab as plt
import ogr

try:
    from pypismtools import unit_converter, smooth
except:
    from pypismtools.pypismtools import unit_converter, smooth

all_basins = ['CW', 'NE', 'NO', 'NW', 'SE', 'SW', 'GR']
# Set up the option parser
parser = ArgumentParser()
parser.description = "A script for PISM output files to time series plots using pylab/matplotlib."
parser.add_argument("FILE", nargs='*')
parser.add_argument("--bounds", dest="bounds", nargs=2, type=float,
                    help="lower and upper bound for ordinate, eg. -1 1", default=None)
parser.add_argument("--time_bounds", dest="time_bounds", nargs=2, type=float,
                    help="lower and upper bound for abscissa, eg. 1990 2000", default=[2009, 3000])
parser.add_argument("-b", "--basin", dest="basin",
                    choices=all_basins,
                    help="Basin to plot", default='GR')
parser.add_argument("-s", "--switch_sign", dest="switch_sign", action='store_true',
                    help="Switch sign of data", default=False)
parser.add_argument("-l", "--labels", dest="labels",
                    help="comma-separated list with labels, put in quotes like 'label 1,label 2'", default=None)
parser.add_argument("-f", "--output_format", dest="out_formats",
                    help="Comma-separated list with output graphics suffix, default = pdf", default='pdf')
parser.add_argument("-n", "--normalize", dest="normalize", action="store_true",
                    help="Normalize to beginning of time series, Default=False", default=False)
parser.add_argument("-o", "--output_file", dest="outfile",
                    help="output file name without suffix, i.e. ts_control -> ts_control_variable", default='unnamed')
parser.add_argument("--step", dest="step", type=int,
                    help="step for plotting values, if time-series is very long", default=1)
parser.add_argument("--start_year", dest="start_year", type=float,
                    help='''Start year''', default=2008)
parser.add_argument("--rotate_xticks", dest="rotate_xticks", action="store_true",
                    help="rotate x-ticks by 30 degrees, Default=False",
                    default=False)
parser.add_argument("-r", "--output_resolution", dest="out_res",
                    help='''Resolution ofoutput graphics in dots per
                  inch (DPI), default = 300''', default=300)
parser.add_argument("--runmean", dest="runmean", type=int,
                    help='''Calculate running mean''', default=None)
parser.add_argument("-t", "--twinx", dest="twinx", action="store_true",
                    help='''adds a second ordinate with units mmSLE,
                  Default=False''', default=False)
parser.add_argument("--plot", dest="plot",
                    help='''What to plot.''',
                    choices=['basin_discharge', 'basin_smb', 'rel_basin_discharge', 'basin_mass', 'basin_mass_d',
                             'basin_d_cumulative',
                             'flood_gates',
                             'per_basin_fluxes', 'per_basin_cumulative', 'rcp_mass', 'rcp_lapse_mass', 'rcp_d'],
                    default='basin_discharge')

parser.add_argument("--title", dest="title",
                    help='''Plot title.''', default=None)

options = parser.parse_args()
basin = options.basin
ifiles = options.FILE
if options.labels != None:
    labels = options.labels.split(',')
else:
    labels = None
bounds = options.bounds
runmean = options.runmean
time_bounds = options.time_bounds
normalize = options.normalize
out_res = options.out_res
outfile = options.outfile
out_formats = options.out_formats.split(',')
plot = options.plot
rotate_xticks = options.rotate_xticks
step = options.step
title = options.title
twinx = options.twinx
dashes = ['-', '--', '-.', ':', '-', '--', '-.', ':']

dx, dy = 4. / out_res, -4. / out_res

# Conversion between giga tons (Gt) and millimeter sea-level equivalent (mmSLE)
gt2mmSLE = 1. / 365
gt2mSLE = 1. / 365 / 1000.

start_year = options.start_year

# Plotting styles
axisbg = '1'
shadow_color = '0.25'
numpoints = 1

fontsize = 6
lw = 0.5
aspect_ratio = 0.35
markersize = 2
fig_width = 3.15  # inch
fig_height = aspect_ratio * fig_width  # inch
fig_size = [fig_width, fig_height]

params = {'backend': 'ps',
          'axes.linewidth': 0.25,
          'lines.linewidth': lw,
          'axes.labelsize': fontsize,
          'font.size': fontsize,
          'xtick.direction': 'in',
          'xtick.labelsize': fontsize,
          'xtick.major.size': 2.5,
          'xtick.major.width': 0.25,
          'ytick.direction': 'in',
          'ytick.labelsize': fontsize,
          'ytick.major.size': 2.5,
          'ytick.major.width': 0.25,
          'legend.fontsize': fontsize,
          'lines.markersize': markersize,
          'font.size': fontsize,
          'figure.figsize': fig_size}

plt.rcParams.update(params)


basin_col_dict = {'SW': '#542788',
                  'CW': '#b35806',
                  'NE': '#e08214',
                  'NO': '#fdb863',
                  'NW': '#b2abd2',
                  'SE': '#8073ac',
                  'GR': '#000000'}

rcp_col_dict = {'CTRL': 'k',
                'RCP85': '#d94701',
                'RCP45': '#fd8d3c',
                'RCP26': '#fdbe85'}

rcp_list = ['RCP26', 'RCP45', 'RCP85']
rcp_dict = {'RCP26': 'RCP 2.6',
            'RCP45': 'RCP 4.5',
            'RCP85': 'RCP 8.5',
            'CTRL': 'CTRL'}

flux_to_mass_vars_dict = {'tendency_of_ice_mass': 'ice_mass',
             'tendency_of_ice_mass_due_to_flow': 'flow_cumulative',
             'tendency_of_ice_mass_due_to_conservation_error': 'conservation_error_cumulative',
             'tendency_of_ice_mass_due_to_basal_mass_flux': 'basal_mass_flux_cumulative',
             'tendency_of_ice_mass_due_to_surface_mass_flux': 'surface_mass_flux_cumulative',
             'tendency_of_ice_mass_due_to_discharge': 'discharge_cumulative'}
flux_vars = flux_to_mass_vars_dict.keys()

flux_abbr_dict = {'tendency_of_ice_mass': '$\dot \mathregular{M}$',
                  'tendency_of_ice_mass_due_to_flow': 'divQ',
                  'tendency_of_ice_mass_due_to_conservation_error': '\dot e',
                  'tendency_of_ice_mass_due_to_basal_mass_flux': 'BMB',
                  'tendency_of_ice_mass_due_to_surface_mass_flux': 'SMB',
                  'tendency_of_ice_mass_due_to_discharge': 'D'}

flux_short_dict = {'tendency_of_ice_mass': 'dmdt',
                  'tendency_of_ice_mass_due_to_flow': 'divq',
                  'tendency_of_ice_mass_due_to_conservation_error': 'e',
                  'tendency_of_ice_mass_due_to_basal_mass_flux': 'bmb',
                  'tendency_of_ice_mass_due_to_surface_mass_flux': 'smb',
                  'tendency_of_ice_mass_due_to_discharge': 'd'}


flux_style_dict = {'tendency_of_ice_mass': '-',
             'tendency_of_ice_mass_due_to_flow': ':',
             'tendency_of_ice_mass_due_to_conservation_error': ':',
             'tendency_of_ice_mass_due_to_basal_mass_flux': '-.',
             'tendency_of_ice_mass_due_to_surface_mass_flux': ':',
             'tendency_of_ice_mass_due_to_discharge': '--'}

mass_abbr_dict = {'ice_mass': 'M',
             'flow_cumulative': 'Q',
             'conservation_error_cumulative': 'e',
             'basal_mass_flux_cumulative': 'BMB',
             'surface_mass_flux_cumulative': 'SMB',
             'discharge_cumulative': 'D'}

mass_style_dict = {'ice_mass': '-',
             'flow_cumulative': ':',
             'conservation_error_cumulative': ':',
             'basal_mass_flux_cumulative': '-.',
             'surface_mass_flux_cumulative': ':',
             'discharge_cumulative': '--'}

flux_plot_vars = ['tendency_of_ice_mass_due_to_discharge', 'tendency_of_ice_mass_due_to_surface_mass_flux']
mass_plot_vars = ['ice_mass']

flux_ounits = 'Gt year-1'
mass_ounits = 'Gt'

def plot_flood_gate_length_ts():
    '''
    Plot time-series length of flood gates
    '''
    driver = ogr.GetDriverByName('ESRI Shapefile')

    fig = plt.figure()
    ax = fig.add_subplot(111, axisbg=axisbg)
    
    for k, rcp in enumerate(rcp_list):
        ifile = ifiles[k]
        print('reading {}'.format(ifile))
        print ifile
        ds = driver.Open(ifile)
        layer = ds.GetLayer()
        cnt = layer.GetFeatureCount()
        
        dates = []
        t = []
        lengths = []

        for feature in layer:
            dates.append(feature.GetField('timestamp'))
            t.append(feature.GetField('timestep'))
            geom = feature.GetGeometryRef()
            length = geom.GetArea() / 2.
            lengths.append(length)

        del ds

        dates = np.array(dates)
        t = np.array(t)
        lengths = np.array(lengths)
        ax.plot(t + start_year, lengths / 1e3,
                color=rcp_col_dict[rcp],
                lw=0.5,
                label=rcp_dict[rcp])

    legend = ax.legend(loc="upper right",
                       edgecolor='0',
                       bbox_to_anchor=(0, 0, .35, 0.87),
                       bbox_transform=plt.gcf().transFigure)
    legend.get_frame().set_linewidth(0.0)
    
    ax.set_xlabel('Year (CE)')
    ax.set_ylabel('length (km)')
        
    if time_bounds:
        ax.set_xlim(time_bounds[0], time_bounds[1])

    if bounds:
        ax.set_ylim(bounds[0], bounds[1])

    ymin, ymax = ax.get_ylim()

    if rotate_xticks:
        ticklabels = ax.get_xticklabels()
        for tick in ticklabels:
                tick.set_rotation(30)
    else:
        ticklabels = ax.get_xticklabels()
        for tick in ticklabels:
            tick.set_rotation(0)
                    
    if title is not None:
            plt.title(title)

    for out_format in out_formats:
        out_file = outfile  + '.' + out_format
        print "  - writing image %s ..." % out_file
        fig.savefig(out_file, bbox_inches='tight', dpi=out_res)

        

def plot_fluxes(plot_vars):

    ifile = ifiles[0]
    nc = NC(ifile, 'r')
    t = nc.variables["time"][:]

    date = np.arange(start_year + step,
                 start_year + (len(t[:]) + 1) * step,
                 step)
    
    fig = plt.figure()
    offset = transforms.ScaledTranslation(dx, dy, fig.dpi_scale_trans)
    ax = fig.add_subplot(111, axisbg=axisbg)
    
    for mvar in plot_vars:
        var_vals = np.squeeze(nc.variables[mvar][:])
        iunits = nc.variables[mvar].units

        var_vals = unit_converter(var_vals, iunits, flux_ounits)
        if runmean is not None:
            runmean_var_vals = smooth(var_vals, window_len=runmean)
            plt.plot(date[:], var_vals[:],
                     color=basin_col_dict[basin],
                     lw=0.25,
                     ls=flux_style_dict[mvar],
                     label=flux_abbr_dict[mvar])
            plt.plot(date[:], runmean_var_vals[:],
                     color=basin_col_dict[basin],
                     lw=0.5,
                     ls=flux_style_dict[mvar])
        else:
            plt.plot(date[:], var_vals[:],
                     color=basin_col_dict[basin],
                     lw=0.5,
                     ls=flux_style_dict[mvar],
                     label=flux_abbr_dict[mvar])

    nc.close()
    
    legend = ax.legend(loc="upper right",
                       edgecolor='0',
                       bbox_to_anchor=(0, 0, 1.15, 1),
                       bbox_transform=plt.gcf().transFigure)
    legend.get_frame().set_linewidth(0.2)

    if twinx:
        axSLE = ax.twinx()
        ax.set_autoscalex_on(False)
        axSLE.set_autoscalex_on(False)
        
    ax.set_xlabel('Year (CE)')
    ax.set_ylabel('mass flux (Gt yr$^{\mathregular{-1}}$)')
            
    if time_bounds:
        ax.set_xlim(time_bounds[0], time_bounds[1])

    if bounds:
        ax.set_ylim(bounds[0], bounds[1])

    ymin, ymax = ax.get_ylim()
    if twinx:
        # Plot twin axis on the right, in mmSLE
        yminSLE = ymin * gt2mmSLE
        ymaxSLE = ymax * gt2mmSLE
        axSLE.set_xlim(date_start, date_end)
        axSLE.set_ylim(yminSLE, ymaxSLE)
        axSLE.set_ylabel(sle_label)

    if rotate_xticks:
        ticklabels = ax.get_xticklabels()
        for tick in ticklabels:
            tick.set_rotation(30)
    else:
        ticklabels = ax.get_xticklabels()
        for tick in ticklabels:
            tick.set_rotation(0)
                    
    if title is not None:
        plt.title(title)

    for out_format in out_formats:
        out_file = outfile + '_fluxes'  + '.' + out_format
        print "  - writing image %s ..." % out_file
        fig.savefig(out_file, bbox_inches='tight', dpi=out_res)


def plot_rcp_mass(plot_var=mass_plot_vars):
    
    fig = plt.figure()
    offset = transforms.ScaledTranslation(dx, dy, fig.dpi_scale_trans)
    ax = fig.add_subplot(111, axisbg=axisbg)

    for k, rcp in enumerate(rcp_list):
        ifile = ifiles[k]
        print('reading {}'.format(ifile))
        nc = NC(ifile, 'r')
        t = nc.variables["time"][:]

        date = np.arange(start_year + step,
                         start_year + (len(t[:]) + 1) * step,
                         step) 
        mvar = plot_var
        var_vals = np.squeeze(nc.variables[mvar][:])
        iunits = nc.variables[mvar].units
        var_vals = -unit_converter(var_vals, iunits, mass_ounits) * gt2mSLE
        plt.plot(date[:], var_vals[:],
                 color=rcp_col_dict[rcp],
                 lw=0.5,
                 label=rcp_dict[rcp])
        nc.close()

    legend = ax.legend(loc="upper right",
                       edgecolor='0',
                       bbox_to_anchor=(0, 0, .35, 0.87),
                       bbox_transform=plt.gcf().transFigure)
    legend.get_frame().set_linewidth(0.0)
    
    ax.set_xlabel('Year (CE)')
    ax.set_ylabel('$\Delta$(GMSL) (m)')
        
    if time_bounds:
        ax.set_xlim(time_bounds[0], time_bounds[1])

    if bounds:
        ax.set_ylim(bounds[0], bounds[1])

    ymin, ymax = ax.get_ylim()

    if rotate_xticks:
        ticklabels = ax.get_xticklabels()
        for tick in ticklabels:
                tick.set_rotation(30)
    else:
        ticklabels = ax.get_xticklabels()
        for tick in ticklabels:
            tick.set_rotation(0)
                    
    if title is not None:
            plt.title(title)

    for out_format in out_formats:
        out_file = outfile + '_rcp' + '_'  + plot_var + '.' + out_format
        print "  - writing image %s ..." % out_file
        fig.savefig(out_file, bbox_inches='tight', dpi=out_res)


def plot_rcp_lapse_mass(plot_var=mass_plot_vars):
    
    fig = plt.figure()
    offset = transforms.ScaledTranslation(dx, dy, fig.dpi_scale_trans)
    ax = fig.add_subplot(111, axisbg=axisbg)

    print ifiles

    sle_lapse_6 = []
    for k, rcp in enumerate(rcp_list):
        ifile = ifiles[k]
        print('reading {}'.format(ifile))
        nc = NC(ifile, 'r')
        t = nc.variables["time"][:]

        date = np.arange(start_year + step,
                         start_year + (len(t[:]) + 1) * step,
                         step) 
        mvar = plot_var
        var_vals = np.squeeze(nc.variables[mvar][:])
        iunits = nc.variables[mvar].units
        var_vals = -unit_converter(var_vals, iunits, mass_ounits) * gt2mSLE
        sle_lapse_6.append(var_vals[-1])
        plt.plot(date[:], var_vals[:],
                 color=rcp_col_dict[rcp],
                 lw=0.5,
                 label=rcp_dict[rcp])
        nc.close()
    m = k
    sle_lapse_0 = []
    for k, rcp in enumerate(rcp_list):
        ifile = ifiles[k+m+1]
        print('reading {}'.format(ifile))
        nc = NC(ifile, 'r')
        t = nc.variables["time"][:]

        date = np.arange(start_year + step,
                         start_year + (len(t[:]) + 1) * step,
                         step) 
        mvar = plot_var
        var_vals = np.squeeze(nc.variables[mvar][:])
        iunits = nc.variables[mvar].units
        var_vals = -unit_converter(var_vals, iunits, mass_ounits) * gt2mSLE
        sle_lapse_0.append(var_vals[-1])
        plt.plot(date[:], var_vals[:],
                 color=rcp_col_dict[rcp],
                 lw=0.5,
                 ls=':')
        nc.close()

    for k, rcp in enumerate(rcp_list):
        x_sle, y_sle = time_bounds[-1], sle_lapse_6[k]
        sle_percent_diff = (sle_lapse_6[k] - sle_lapse_0[k]) / sle_lapse_0[k] * 100
        plt.text( x_sle, y_sle, '{: 3.0f}%'.format(sle_percent_diff),
                          color=rcp_col_dict[rcp])

    legend = ax.legend(loc="upper right",
                       edgecolor='0',
                       bbox_to_anchor=(0, 0, .35, 0.87),
                       bbox_transform=plt.gcf().transFigure)
    legend.get_frame().set_linewidth(0.0)
    
    ax.set_xlabel('Year (CE)')
    ax.set_ylabel('$\Delta$(GMSL) (m)')
        
    if time_bounds:
        ax.set_xlim(time_bounds[0], time_bounds[1])

    if bounds:
        ax.set_ylim(bounds[0], bounds[1])

    ymin, ymax = ax.get_ylim()

    if rotate_xticks:
        ticklabels = ax.get_xticklabels()
        for tick in ticklabels:
                tick.set_rotation(30)
    else:
        ticklabels = ax.get_xticklabels()
        for tick in ticklabels:
            tick.set_rotation(0)
                    
    if title is not None:
            plt.title(title)

    for out_format in out_formats:
        out_file = outfile + '_rcp' + '_'  + plot_var + '.' + out_format
        print "  - writing image %s ..." % out_file
        fig.savefig(out_file, bbox_inches='tight', dpi=out_res)


def plot_fluxes_by_basin(plot_vars=['tendency_of_ice_mass', 'tendency_of_ice_mass_due_to_discharge', 'tendency_of_ice_mass_due_to_surface_mass_flux']):
    '''
    Make a plot per basin with all flux_plot_vars
    '''
    
    for k, ifile in enumerate(ifiles):

        fig = plt.figure()
        offset = transforms.ScaledTranslation(dx, dy, fig.dpi_scale_trans)
        ax = fig.add_subplot(111, axisbg=axisbg)

        basin = all_basins[k]
        print('reading {}'.format(ifile))
        nc = NC(ifile, 'r')
        t = nc.variables["time"][:]

        date = np.arange(start_year + step,
                         start_year + (len(t[:]) + 1) * step,
                         step) 

        for mvar in plot_vars:
            var_vals = np.squeeze(nc.variables[mvar][:])
            iunits = nc.variables[mvar].units

            var_vals = -unit_converter(var_vals, iunits, flux_ounits) * gt2mSLE
            if runmean is not None:
                runmean_var_vals = smooth(var_vals, window_len=runmean)
                plt.plot(date[:], var_vals[:],
                         color=basin_col_dict[basin],
                         lw=0.25,
                         ls=flux_style_dict[mvar])
                plt.plot(date[:], runmean_var_vals[:],
                         color=basin_col_dict[basin],
                         lw=0.5,
                         ls=flux_style_dict[mvar],
                         label=flux_abbr_dict[mvar])
            else:
                plt.plot(date[:], var_vals[:],
                         color=basin_col_dict[basin],
                         lw=0.5,
                         ls=flux_style_dict[mvar],
                         label=flux_abbr_dict[mvar])
        nc.close()

        legend = ax.legend(loc="upper right",
                           edgecolor='0',
                           bbox_to_anchor=(0, 0, 1.15, 1),
                           bbox_transform=plt.gcf().transFigure)
        legend.get_frame().set_linewidth(0.2)
    
        ax.set_xlabel('Year (CE)')
        ax.set_ylabel('mass flux (Gt yr$^{\mathregular{-1}}$)')
        
        if time_bounds:
            ax.set_xlim(time_bounds[0], time_bounds[1])
            
        if bounds:
            ax.set_ylim(bounds[0], bounds[1])

        if rotate_xticks:
            ticklabels = ax.get_xticklabels()
            for tick in ticklabels:
                tick.set_rotation(30)
        else:
            ticklabels = ax.get_xticklabels()
            for tick in ticklabels:
                tick.set_rotation(0)
                    
        if title is not None:
            plt.title(title)

        for out_format in out_formats:
            out_file = outfile + '_basin_{}'.format(basin)  + '_fluxes.' + out_format
            print "  - writing image %s ..." % out_file
            fig.savefig(out_file, bbox_inches='tight', dpi=out_res)


def plot_cumulative_fluxes_by_basin(plot_vars=['ice_mass', 'discharge_cumulative', 'surface_mass_flux_cumulative']):
    '''
    Make a plot per basin with all flux_plot_vars
    '''
    
    for k, ifile in enumerate(ifiles):

        fig = plt.figure()
        offset = transforms.ScaledTranslation(dx, dy, fig.dpi_scale_trans)
        ax = fig.add_subplot(111, axisbg=axisbg)

        basin = all_basins[k]
        print('reading {}'.format(ifile))
        nc = NC(ifile, 'r')
        t = nc.variables["time"][:]

        date = np.arange(start_year + step,
                         start_year + (len(t[:]) + 1) * step,
                         step) 
        idx = np.where(np.array(date) == time_bounds[-1])[0][0]

        for mvar in plot_vars:
            if mvar=='discharge_cumulative':
                d_var_vals_sum = 0
                for d_var in ('discharge_cumulative', 'basal_mass_flux_cumulative'):
                    d_var_vals = -np.squeeze(nc.variables[d_var][:]) * gt2mSLE
                    iunits = nc.variables[d_var].units
                    d_var_vals_sum += unit_converter(d_var_vals, iunits, mass_ounits)
                var_vals = d_var_vals_sum
            else:
                var_vals = np.squeeze(nc.variables[mvar][:])
                iunits = nc.variables[mvar].units
                var_vals = unit_converter(var_vals, iunits, mass_ounits)
            if runmean is not None:
                runmean_var_vals = smooth(var_vals, window_len=runmean)
                plt.plot(date[:], var_vals[:],
                         color=basin_col_dict[basin],
                         lw=0.25,
                         ls=mass_style_dict[mvar])
                plt.plot(date[:], runmean_var_vals[:],
                         color=basin_col_dict[basin],
                         lw=0.5,
                         ls=mass_style_dict[mvar],
                         label=mass_abbr_dict[mvar])
            else:
                plt.plot(date[:], var_vals[:],
                         color=basin_col_dict[basin],
                         lw=0.5,
                         ls=mass_style_dict[mvar],
                         label=mass_abbr_dict[mvar])
        nc.close()

        legend = ax.legend(loc="upper right",
                           edgecolor='0',
                           bbox_to_anchor=(0, 0, 1.15, 1),
                           bbox_transform=plt.gcf().transFigure)
        legend.get_frame().set_linewidth(0.2)
    
        ax.set_xlabel('Year (CE)')
        ax.set_ylabel('cumulative mass change (Gt)')
        axSLE = ax.twinx()
        ax.set_autoscalex_on(False)
        axSLE.set_autoscalex_on(False)
            

        ymin, ymax = ax.get_ylim()
        # Plot twin axis on the right, in mmSLE
        yminSLE = ymin * gt2mmSLE
        ymaxSLE = ymax * gt2mmSLE
        axSLE.set_ylim(yminSLE, ymaxSLE)
        axSLE.set_ylabel('mm SLE')

        if time_bounds:
            ax.set_xlim(time_bounds[0], time_bounds[1])
            
        if bounds:
            ax.set_ylim(bounds[0], bounds[1])

        if rotate_xticks:
            ticklabels = ax.get_xticklabels()
            for tick in ticklabels:
                tick.set_rotation(30)
        else:
            ticklabels = ax.get_xticklabels()
            for tick in ticklabels:
                tick.set_rotation(0)
                    
        if title is not None:
            plt.title(title)

        for out_format in out_formats:
            out_file = outfile + '_basin_{}'.format(basin)  + '_cumulative.' + out_format
            print "  - writing image %s ..." % out_file
            fig.savefig(out_file, bbox_inches='tight', dpi=out_res)


def plot_mass(plot_vars=mass_plot_vars):
    '''
    Plot mass time series for all basins in one plot
    '''
    
    fig = plt.figure()
    offset = transforms.ScaledTranslation(dx, dy, fig.dpi_scale_trans)
    ax = fig.add_subplot(111, axisbg=axisbg)

    for ifile in ifiles:
        print('reading {}'.format(ifile))
        nc = NC(ifile, 'r')
        t = nc.variables["time"][:]

        date = np.arange(start_year + step,
                         start_year + (len(t[:]) + 1) * step,
                         step) 

        for mvar in plot_vars:
            var_vals = np.squeeze(nc.variables[mvar][:])
            iunits = nc.variables[mvar].units
            var_vals = unit_converter(var_vals, iunits, mass_ounits)
            # plot anomalies
            plt.plot(date[:], (var_vals[:] - var_vals[0]),
                     color=basin_col_dict[basin],
                     lw=0.5,
                     label=basin)
        nc.close()

    legend = ax.legend(loc="upper right",
                       edgecolor='0',
                       bbox_to_anchor=(0, 0, 1.15, 1),
                       bbox_transform=plt.gcf().transFigure)
    legend.get_frame().set_linewidth(0.2)

    axSLE = ax.twinx()
    ax.set_autoscalex_on(False)
    axSLE.set_autoscalex_on(False)
    
    ax.set_xlabel('Year (CE)')
    ax.set_ylabel('cumulative mass change (Gt)')
        
    if time_bounds:
        ax.set_xlim(time_bounds[0], time_bounds[1])

    if bounds:
        ax.set_ylim(bounds[0], bounds[1])

    ymin, ymax = ax.get_ylim()
    # Plot twin axis on the right, in mmSLE
    yminSLE = ymin * gt2mmSLE
    ymaxSLE = ymax * gt2mmSLE
    axSLE.set_ylim(yminSLE, ymaxSLE)
    axSLE.set_ylabel('mm SLE')

    if rotate_xticks:
        ticklabels = ax.get_xticklabels()
        for tick in ticklabels:
                tick.set_rotation(30)
    else:
        ticklabels = ax.get_xticklabels()
        for tick in ticklabels:
            tick.set_rotation(0)
                    
    if title is not None:
            plt.title(title)

    for out_format in out_formats:
        out_file = outfile + '_mass'  + '.' + out_format
        print "  - writing image %s ..." % out_file
        fig.savefig(out_file, bbox_inches='tight', dpi=out_res)


def plot_flux_all_basins(mvar='tendency_of_ice_mass_due_to_discharge'):
    '''
    Plot discharge flux for all basins in one plot
    '''
    
    fig = plt.figure()
    offset = transforms.ScaledTranslation(dx, dy, fig.dpi_scale_trans)
    ax = fig.add_subplot(111, axisbg=axisbg)

    for k, ifile in enumerate(ifiles):
        basin = all_basins[k]
        print('reading {}'.format(ifile))
        nc = NC(ifile, 'r')
        t = nc.variables["time"][:]

        date = np.arange(start_year + step,
                         start_year + (len(t[:]) + 1) * step,
                         step) 

        var_vals = np.squeeze(nc.variables[mvar][:])
        iunits = nc.variables[mvar].units
        var_vals = unit_converter(var_vals, iunits, flux_ounits)
        if runmean is not None:
            runmean_var_vals = smooth(var_vals, window_len=runmean)
            plt.plot(date[:], var_vals[:],
                     alpha=0.5,
                     color=basin_col_dict[basin],
                     lw=0.25,
                     ls='-')
            plt.plot(date[:], runmean_var_vals[:],
                     color=basin_col_dict[basin],
                     lw=0.5,
                     ls='-',
                     label=basin)
        else:
            plt.plot(date[:], var_vals[:],
                     color=basin_col_dict[basin],
                     lw=0.5,
                     ls='-',
                     label=basin)
        nc.close()

    legend = ax.legend(loc="upper right",
                       edgecolor='0',
                       bbox_to_anchor=(0, 0, 1.07, 0.9),
                       bbox_transform=plt.gcf().transFigure)
    legend.get_frame().set_linewidth(0.2)
    
    ax.set_xlabel('Year (CE)')
    ax.set_ylabel('mass flux (Gt yr$^{\mathregular{-1}}$)')
        
    if time_bounds:
        ax.set_xlim(time_bounds[0], time_bounds[1])

    if bounds:
        ax.set_ylim(bounds[0], bounds[1])

    xmin, xmax = ax.get_xlim()
    ax.hlines(0, xmin, xmax, lw=0.25)

    if rotate_xticks:
        ticklabels = ax.get_xticklabels()
        for tick in ticklabels:
                tick.set_rotation(30)
    else:
        ticklabels = ax.get_xticklabels()
        for tick in ticklabels:
            tick.set_rotation(0)
                    
    if title is not None:
            plt.title(title)

    for out_format in out_formats:
        out_file = outfile + '_{}'.format(flux_short_dict[mvar])  + '.' + out_format
        print "  - writing image %s ..." % out_file
        fig.savefig(out_file, bbox_inches='tight', dpi=out_res)

def plot_rel_discharge_flux_all_basins(mvar='tendency_of_ice_mass_due_to_discharge'):
    
    fig = plt.figure()
    offset = transforms.ScaledTranslation(dx, dy, fig.dpi_scale_trans)
    ax = fig.add_subplot(111, axisbg=axisbg)

    for k, ifile in enumerate(ifiles):
        basin = all_basins[k]
        print('reading {}'.format(ifile))
        nc = NC(ifile, 'r')
        t = nc.variables["time"][:]

        date = np.arange(start_year + step,
                         start_year + (len(t[:]) + 1) * step,
                         step) 

        var_vals = np.squeeze(nc.variables[mvar][:]) * 100 - 100
        ax.plot(date[:], (var_vals[:]),
                 color=basin_col_dict[basin],
                 lw=0.75,
                 label=basin)
        nc.close()

    legend = ax.legend(loc="upper right",
                       edgecolor='0',
                       bbox_to_anchor=(0, 0, 1.15, 1),
                       bbox_transform=plt.gcf().transFigure)
    legend.get_frame().set_linewidth(0.2)
    
    ax.set_xlabel('Year (CE)')
    ax.set_ylabel('mass flux anomaly (%)')
        
    if time_bounds:
        ax.set_xlim(time_bounds[0], time_bounds[1])

    if bounds:
        ax.set_ylim(bounds[0], bounds[1])

    xmin, xmax = ax.get_xlim()
    ax.hlines(0, xmin, xmax, lw=0.25)

    if rotate_xticks:
        ticklabels = ax.get_xticklabels()
        for tick in ticklabels:
                tick.set_rotation(30)
    else:
        ticklabels = ax.get_xticklabels()
        for tick in ticklabels:
            tick.set_rotation(0)
                    
    if title is not None:
            plt.title(title)

    for out_format in out_formats:
        out_file = outfile + '_discharge_flux_anomaly'  + '.' + out_format
        print "  - writing image %s ..." % out_file
        fig.savefig(out_file, bbox_inches='tight', dpi=out_res)

        
def plot_basin_mass(plot_var='ice_mass'):
    
    fig = plt.figure()
    offset = transforms.ScaledTranslation(dx, dy, fig.dpi_scale_trans)
    ax = fig.add_subplot(111, axisbg=axisbg)

    my_var_vals = 0
    print('cumulative SLE {}m'.format(my_var_vals))
    for k, ifile in enumerate(ifiles):
        basin = all_basins[k]
        print('reading {}'.format(ifile))
        nc = NC(ifile, 'r')
        t = nc.variables["time"][:]

        date = np.arange(start_year + step,
                         start_year + (len(t[:]) + 1) * step,
                         step) 

        mvar = plot_var
        if plot_var == 'ice_mass':
            var_vals = -np.squeeze(nc.variables[mvar][:]) * gt2mSLE
            iunits = nc.variables[mvar].units
            var_vals = unit_converter(var_vals, iunits, mass_ounits)
        elif plot_var == 'discharge_cumulative':
            d_var_vals = 0
            for d_var in ('discharge_cumulative', 'basal_mass_flux_cumulative'):
                tmp_d_var_vals = -np.squeeze(nc.variables[d_var][:]) * gt2mSLE
                iunits = nc.variables[d_var].units
                d_var_vals += unit_converter(tmp_d_var_vals, iunits, mass_ounits)
            var_vals = d_var_vals
        else:
            pass    
        # plot anomalies
        ax.fill_between(date[:], my_var_vals, my_var_vals + var_vals[:],
                        color=basin_col_dict[basin],
                        linewidth=0,
                        label=basin)
        offset = 10
        try:
            x_sle, y_sle = time_bounds[-1] + offset, my_var_vals[-1]
        except:  # first iteration
            x_sle, y_sle = time_bounds[-1] + offset, my_var_vals
        print('basin {}: {}'.format(basin, var_vals[-1]))
        plt.text( x_sle, y_sle, '{: 1.2f}'.format(var_vals[-1]),
                          color=basin_col_dict[basin])
        nc.close()
        my_var_vals += var_vals
        print('cumulative SLE {}m'.format(my_var_vals[-1]))

    legend = ax.legend(loc="upper right",
                       edgecolor='0',
                       bbox_to_anchor=(0, 0, 1.15, 1),
                       bbox_transform=plt.gcf().transFigure)
    legend.get_frame().set_linewidth(0.2)
    
    ax.set_xlabel('Year (CE)')
    ax.set_ylabel('$\Delta$(GMSL) (m)')
        
    if time_bounds:
        ax.set_xlim(time_bounds[0], time_bounds[1])

    if bounds:
        ax.set_ylim(bounds[0], bounds[1])

    if rotate_xticks:
        ticklabels = ax.get_xticklabels()
        for tick in ticklabels:
                tick.set_rotation(30)
    else:
        ticklabels = ax.get_xticklabels()
        for tick in ticklabels:
            tick.set_rotation(0)
                    
    if title is not None:
            plt.title(title)

    for out_format in out_formats:
        out_file = outfile + '_' + mvar  + '.' + out_format
        print "  - writing image %s ..." % out_file
        fig.savefig(out_file, bbox_inches='tight', dpi=out_res)

def plot_basin_mass_d():
    
    fig = plt.figure()
    offset = transforms.ScaledTranslation(dx, dy, fig.dpi_scale_trans)
    ax = fig.add_subplot(111, axisbg=axisbg)

    mass_var_vals_positive_cum = 0
    mass_var_vals_negative_cum = 0
    for k, ifile in enumerate(ifiles):
        basin = all_basins[k]
        print('reading {}'.format(ifile))
        nc = NC(ifile, 'r')
        t = nc.variables["time"][:]

        date = np.arange(start_year + step,
                         start_year + (len(t[:]) + 1) * step,
                         step) 

        idx = np.where(np.array(date) == time_bounds[-1])[0][0]

        mvar = 'ice_mass'
        mass_var_vals = -np.squeeze(nc.variables[mvar][:]) * gt2mSLE
        iunits = nc.variables[mvar].units
        mass_var_vals = unit_converter(mass_var_vals, iunits, mass_ounits)
        if mass_var_vals[idx] > 0:
            ax.fill_between(date[:], mass_var_vals_positive_cum, mass_var_vals_positive_cum + mass_var_vals[:],
                            color=basin_col_dict[basin],
                            linewidth=0,
                            label=basin)
        else:
            print mass_var_vals[idx]
            ax.fill_between(date[:], mass_var_vals_negative_cum, mass_var_vals_negative_cum + mass_var_vals[:],
                            color=basin_col_dict[basin],
                            linewidth=0,
                            label=basin)
            plt.rcParams['hatch.color'] = basin_col_dict[basin]
            plt.rcParams['hatch.linewidth'] = 0.1
            ax.fill_between(date[:], mass_var_vals_negative_cum, mass_var_vals_negative_cum + mass_var_vals[:],
                            facecolor="none", hatch="XXXXX", edgecolor="k",
                            linewidth=0.0)
        d_var_vals_sum = 0
        for d_var in ['discharge_cumulative', 'basal_mass_flux_cumulative']:
            d_var_vals = -np.squeeze(nc.variables[d_var][:]) * gt2mSLE
            iunits = nc.variables[d_var].units
            d_var_vals_sum += unit_converter(d_var_vals, iunits, mass_ounits)
        # if mass_var_vals[idx] > 0:
        #     ax.fill_between(date[:], mass_var_vals_positive_cum, mass_var_vals_positive_cum + d_var_vals_sum[:],
        #                     color='0.8',
        #                     alpha=0.5,
        #                     linewidth=0)

        if mass_var_vals[idx] > 0:
            ax.plot(date[:], mass_var_vals_positive_cum + mass_var_vals[:],
                    color='k',
                    linewidth=0.1)
        else:
            ax.plot(date[:], mass_var_vals_negative_cum + mass_var_vals[:],
                    color='k',
                    linewidth=0.1)

        offset = 0
        if mass_var_vals[idx] > 0:
            try:
                x_sle, y_sle = date[idx] + offset, mass_var_vals_positive_cum[idx]
            except:  # first iteratio
                x_sle, y_sle = date[idx] + offset, mass_var_vals_positive_cum
        else:
            try:
                x_sle, y_sle = date[idx] + offset, mass_var_vals_negative_cum[idx] + mass_var_vals[idx] 
            except:  # first iteration
                x_sle, y_sle = date[idx] + offset, mass_var_vals_negative_cum + mass_var_vals[idx] 
        # contribution of cumulative discharge to cumulative mass loss
        d_to_mass_percent = d_var_vals_sum[idx] / mass_var_vals[idx] * 100
        print basin, d_to_mass_percent ,d_var_vals_sum[idx], mass_var_vals[idx]
        if d_to_mass_percent > 0:
            plt.text( x_sle, y_sle, '{: 3.0f}%'.format(d_to_mass_percent),
                      color=basin_col_dict[basin])
        # plt.text( x_sle, y_sle, '{: 1.2f}m'.format(mass_var_vals[idx]),
        #           color=basin_col_dict[basin])
        nc.close()
        if mass_var_vals[idx] > 0:
            mass_var_vals_positive_cum += mass_var_vals
        else:
            mass_var_vals_negative_cum += mass_var_vals

    ax.hlines(0, time_bounds[0], time_bounds[-1], lw=0.25)

    legend = ax.legend(loc="upper right",
                       edgecolor='0',
                       bbox_to_anchor=(0, 0, 1.15, 1),
                       bbox_transform=plt.gcf().transFigure)
    legend.get_frame().set_linewidth(0.2)
    
    ax.set_xlabel('Year (CE)')
    ax.set_ylabel('$\Delta$(GMSL) (m)')
        
    if time_bounds:
        ax.set_xlim(time_bounds[0], time_bounds[1])

    if bounds:
        ax.set_ylim(bounds[0], bounds[-1])

    if rotate_xticks:
        ticklabels = ax.get_xticklabels()
        for tick in ticklabels:
                tick.set_rotation(30)
    else:
        ticklabels = ax.get_xticklabels()
        for tick in ticklabels:
            tick.set_rotation(0)
                    
    if title is not None:
            plt.title(title)

    for out_format in out_formats:
        out_file = outfile + '_' + mvar  + '.' + out_format
        print "  - writing image %s ..." % out_file
        fig.savefig(out_file, bbox_inches='tight', dpi=out_res)

if plot == 'basin_discharge':
    plot_flux_all_basins()
elif plot == 'basin_smb':
    plot_flux_all_basins(plot_vars='tendency_of_ice_mass_due_to_surface_mass_flux')
elif plot == 'rel_basin_discharge':
    plot_rel_discharge_flux_all_basins()
elif plot == 'basin_mass':
    plot_basin_mass()
elif plot == 'basin_mass_d':
    plot_basin_mass_d()
elif plot == 'basin_d_cumulative':
    plot_basin_mass(plot_var='discharge_cumulative')
elif plot == 'per_basin_fluxes':
    plot_fluxes_by_basin()
elif plot == 'per_basin_cumulative':
    plot_cumulative_fluxes_by_basin()
elif plot == 'rcp_mass':
    plot_rcp_mass(plot_var='ice_mass')
elif plot == 'rcp_lapse_mass':
    plot_rcp_lapse_mass(plot_var='ice_mass')
elif plot == 'rcp_d':
    plot_rcp_mass(plot_var='discharge_cumulative')
elif plot == 'flood_gates':
    plot_flood_gate_length_ts()