#!/usr/bin/env python

# Copyright (C) 2017 Andy Aschwanden

import numpy as np
import pylab as plt
from argparse import ArgumentParser
import matplotlib.transforms as transforms
from netCDF4 import Dataset as NC

try:
    from pypismtools import unit_converter, set_mode, get_golden_mean, smooth
except:
    from pypismtools.pypismtools import unit_converter, set_mode, get_golden_mean, smooth

all_basins = ['CW', 'NE', 'NO', 'NW', 'SE', 'SW', 'GR']
# Set up the option parser
parser = ArgumentParser()
parser.description = "A script for PISM output files to time series plots using pylab/matplotlib."
parser.add_argument("FILE", nargs='*')
parser.add_argument("--bounds", dest="bounds", nargs=2, type=float,
                    help="lower and upper bound for ordinate, eg. -1 1", default=None)
parser.add_argument("--time_bounds", dest="time_bounds", nargs=2, type=float,
                    help="lower and upper bound for abscissa, eg. 1990 2000", default=None)
parser.add_argument("-a", "--aspect_ratio", dest="aspect_ratio", type=float,
                    help="Plot aspect ratio", default=0.75)
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
parser.add_argument("-p", "--print_size", dest="print_mode",
                    help="sets figure size and font size, available options are: \
                  'onecol','publish','medium','presentation','twocol'", default="medium")
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
                    choices=['basin_discharge', 'rel_basin_discharge', 'basin_mass', 'per_basin_fluxes', 'per_basin_cumulative'],
                    default='basin_discharge')

parser.add_argument("--title", dest="title",
                    help='''Plot title.''', default=None)

options = parser.parse_args()
aspect_ratio = options.aspect_ratio
basin = options.basin
ifiles = options.FILE
if options.labels != None:
    labels = options.labels.split(',')
else:
    labels = None
bounds = options.bounds
runmean = options.runmean
time_bounds = options.time_bounds
golden_mean = get_golden_mean()
normalize = options.normalize
out_res = options.out_res
outfile = options.outfile
out_formats = options.out_formats.split(',')
print_mode = options.print_mode
plot = options.plot
rotate_xticks = options.rotate_xticks
step = options.step
title = options.title
twinx = options.twinx
dashes = ['-', '--', '-.', ':', '-', '--', '-.', ':']

dx, dy = 4. / out_res, -4. / out_res

# Conversion between giga tons (Gt) and millimeter sea-level equivalent (mmSLE)
gt2mmSLE = 1. / 365

start_year = options.start_year

# Plotting styles
axisbg = '1'
shadow_color = '0.25'
numpoints = 1

# set the print mode
lw, pad_inches = set_mode(print_mode, aspect_ratio=aspect_ratio)


basin_col_dict = {'CW': '#542788',
                  'NE': '#b35806',
                  'NO': '#e08214',
                  'NW': '#fdb863',
                  'SE': '#b2abd2',
                  'SW': '#8073ac',
                  'GR': '#000000'}

rcp_col_dict = {'RCP85': '#ca0020',
                'RCP60': '#f4a582',
                'RCP45': '#92c5de',
                'RCP26': '#0571b0'}

rcp_list = ['RCP26', 'RCP45', 'RCP63', 'RCP85']
rcp_dict = {'RCP26': 'RCP 2.6',
            'RCP45': 'RCP 4.5',
            'RCP60': 'RCP 6.0',
            'RCP85': 'RCP 8.5'}

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
                     lw=1,
                     ls=flux_style_dict[mvar])
        else:
            plt.plot(date[:], var_vals[:],
                     color=basin_col_dict[basin],
                     lw=1,
                     ls=flux_style_dict[mvar],
                     label=flux_abbr_dict[mvar])

    nc.close()
    
    ax.legend(loc="upper right",
              edgecolor='0',
              bbox_to_anchor=(0, 0, 1.15, 1),
                  bbox_transform=plt.gcf().transFigure)

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


def plot_rcp(plot_vars=mass_plot_vars):
    
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

        for mvar in plot_vars:
            var_vals = np.squeeze(nc.variables[mvar][:])
            iunits = nc.variables[mvar].units
            var_vals = unit_converter(var_vals, iunits, mass_ounits)
            # plot anomalies
            plt.plot(date[:], (var_vals[:] - var_vals[0]),
                     color=rcp_col_dict[rcp],
                     lw=0.75,
                     label=rcp_dict[rcp])
        nc.close()

    ax.legend(loc="upper right",
              edgecolor='0',
              bbox_to_anchor=(0, 0, 1.15, 1),
              bbox_transform=plt.gcf().transFigure)

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

            var_vals = unit_converter(var_vals, iunits, flux_ounits)
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

        ax.legend(loc="upper right",
                  edgecolor='0',
                  bbox_to_anchor=(0, 0, 1.15, 1),
                  bbox_transform=plt.gcf().transFigure)
    
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

        for mvar in plot_vars:
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

        ax.legend(loc="upper right",
                  edgecolor='0',
                  bbox_to_anchor=(0, 0, 1.15, 1),
                  bbox_transform=plt.gcf().transFigure)
    
        ax.set_xlabel('Year (CE)')
        ax.set_ylabel('cumulative mass change (Gt)')
        
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
                     lw=0.75,
                     label=basin)
        nc.close()

    ax.legend(loc="upper right",
              edgecolor='0',
              bbox_to_anchor=(0, 0, 1.15, 1),
              bbox_transform=plt.gcf().transFigure)

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


def plot_discharge_flux_all_basins(mvar='tendency_of_ice_mass_due_to_discharge'):
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
                     color=basin_col_dict[basin],
                     lw=0.25,
                     ls='-')
            plt.plot(date[:], runmean_var_vals[:],
                     color=basin_col_dict[basin],
                     lw=0.75,
                     ls='-',
                     label=basin)
        else:
            plt.plot(date[:], var_vals[:],
                     color=basin_col_dict[basin],
                     lw=0.75,
                     ls='-',
                     label=basin)
        nc.close()

    ax.legend(loc="upper right",
              edgecolor='0',
              bbox_to_anchor=(0, 0, 1.15, 1),
              bbox_transform=plt.gcf().transFigure)
    
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
        out_file = outfile + '_discharge_flux'  + '.' + out_format
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

    ax.legend(loc="upper right",
              shadow=False,
              bbox_to_anchor=(0, 0, 1, 1),
              bbox_transform=plt.gcf().transFigure)
    
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

        
def plot_basin_mass(plot_vars=mass_plot_vars):
    
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

        for mvar in plot_vars:
            var_vals = np.squeeze(nc.variables[mvar][:])
            iunits = nc.variables[mvar].units
            var_vals = unit_converter(var_vals, iunits, mass_ounits)
            # plot anomalies
            plt.plot(date[:], (var_vals[:] - var_vals[0]),
                     color=basin_col_dict[basin],
                     lw=0.75,
                     label=basin)
        nc.close()

    ax.legend(loc="upper right",
              shadow=False,
              bbox_to_anchor=(0, 0, 1, 1),
              bbox_transform=plt.gcf().transFigure)

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


if plot == 'basin_discharge':
    plot_discharge_flux_all_basins()
elif plot == 'rel_basin_discharge':
    plot_rel_discharge_flux_all_basins()
elif plot == 'basin_mass':
    plot_basin_mass()
elif plot == 'per_basin_fluxes':
    plot_fluxes_by_basin()
elif plot == 'per_basin_cumulative':
    plot_cumulative_fluxes_by_basin()
