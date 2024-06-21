import subprocess
import os
import sys

import serial
from pyubx2 import UBXReader
import time


import matplotlib.pyplot as plt
import matplotlib.dates as md
import numpy as np
import pandas as pd

import simplekml # Create .kml files 
import pymap3d as pm

from typing import List


def plt_northEast(enu, smode):
    """
    Plots easting and northing

    :enu: array of error components in east, north, and up directions
    :smode: array of modes in each epoch

    """
    east = max(enu[:, 0])
    north = max(enu[:, 1])

    # ylim = east if east >= north else north   # takes the biggest one

    ylim = 3

    idx4 = np.where(smode == 4)[0]
    idx5 = np.where(smode == 5)[0]
    idx0 = np.where(smode == 0)[0]

    _ = plt.figure(figsize=[6,6])
    plt.plot(enu[idx0, 0],enu[idx0, 1], 'r.', label='standalone')
    plt.plot(enu[idx5, 0],enu[idx5, 1], 'y.', label='float')
    plt.plot(enu[idx4, 0],enu[idx4, 1], 'g.', label='fixed')
    plt.xlabel('easting [m]')
    plt.ylabel('northing [m]')
    plt.axis([-ylim,ylim,-ylim,ylim])
    plt.grid()
    plt.legend()
    plt.show()

def plt_error(t, enu, dmax=0):
    """
    Plots the error with a reference position.
    enu = gn.ecef2enu(pos_ref, sol-xyz_ref)
    
    t: time array
    enu: array of error components in east, north, and up directions
    dmax: maximum distance for y-axis, calculated if not provided
    """
    assert len(t) == len(enu), "Arrays must be the same length"
    assert enu.shape[1] == 3, "enu must have three columns"

    if dmax <= 0:
        # Calculate the maximum distance in the XY plane
        distancias = np.sqrt(enu[:, 0]**2 + enu[:, 1]**2)
        dmax = np.max(distancias) * 1.5  

    plt.figure(figsize=(10, 6))
    # Plot each component ("east" "north" "up")
    plt.plot(t, enu[:, 0], label='east')  # Component 'east'
    plt.plot(t, enu[:, 1], label='north') # Component 'north'
    plt.plot(t, enu[:, 2], label='up')    # Component 'up'

    # Plot conf
    plt.ylabel('pos err[m]')
    plt.xlabel('time[s]')
    plt.legend()
    plt.grid()
    plt.axis([0, max(t), -dmax, dmax])
    plt.title("Componentes East, North, y Up en Función del Tiempo")

    #plt.show()

def plt_NorthEastUp(t, enu, ztd, smode):
    """
    Plot North-East-Up and the ztd(Zenith Total Delay)
    """
    # Check if smode is empty
    if not smode.size:
        print("smode is empty")
        return -1

    idx4 = np.where(smode == 4)[0]
    idx5 = np.where(smode == 5)[0]
    idx0 = np.where(smode == 0)[0]

    fmt = '%H:%M'  # Format
    lbl_t = ['East [m]', 'North [m]', 'Up [m]']

    # Ajustar dinámicamente el ylim basado en los datos
    for k in range(3):
        plt.subplot(4, 1, k+1)
        plt.plot_date(t[idx0], enu[idx0, k], 'r.')
        plt.plot_date(t[idx5], enu[idx5, k], 'y.')
        plt.plot_date(t[idx4], enu[idx4, k], 'g.')
        plt.ylabel(lbl_t[k])
        plt.grid()
        
        # Ajuste de ylim basado en los datos actuales
        data_min = np.min(enu[:, k])
        data_max = np.max(enu[:, k])
        data_range = data_max - data_min
        padding = data_range * 0.1  # Añadir un 10% de margen
        plt.ylim([data_min - padding, data_max + padding])
        
        plt.gca().xaxis.set_major_formatter(md.DateFormatter(fmt))
    
    plt.subplot(4, 1, 4)
    plt.plot_date(t[idx0], ztd[idx0]*1e2, 'r.', markersize=8, label='none')
    plt.plot_date(t[idx5], ztd[idx5]*1e2, 'y.', markersize=8, label='float')
    plt.plot_date(t[idx4], ztd[idx4]*1e2, 'g.', markersize=8, label='fix')
    plt.ylabel('ZTD [cm]')
    plt.grid()
    plt.gca().xaxis.set_major_formatter(md.DateFormatter(fmt))
    plt.xlabel('Time [HH:MM]')
    plt.legend()
    
    # Ajuste de ylim para ZTD basado en los datos actuales
    ztd_min = np.min(ztd) * 1e2
    ztd_max = np.max(ztd) * 1e2
    ztd_range = ztd_max - ztd_min
    padding = ztd_range * 0.1  # Añadir un 10% de margen
    plt.ylim([ztd_min - padding, ztd_max + padding])
    
    #plt.show()

def plt_3D(vector):
    """
    3D plot of a Mx3 vector. 
    """
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    # Representar cada punto
    ax.scatter(vector[:, 0], vector[:, 1], vector[:, 2])
    # Establecer límites y etiquetas
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    plt.title("Representación de Puntos en 3D")
    plt.show()

def plt_components(matrix):
    """
    Plot the East, North, and Up components of a matrix 

    Parameters:
    matrix (array): A numpy array where each row is a vector with East, North, and Up components.
    """
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 6))

    # East component
    ax1.plot(matrix[:, 0], 'r-')
    ax1.set_title('East Component')
    ax1.set_ylabel('East Value')
    ax1.grid(True)

    # North component
    ax2.plot(matrix[:, 1], 'g-')
    ax2.set_title('North Component')
    ax2.set_ylabel('North Value')
    ax2.grid(True)

    # Up component
    ax3.plot(matrix[:, 2], 'b-')
    ax3.set_title('Up Component')
    ax3.set_ylabel('Up Value')
    ax3.set_xlabel('Index')
    ax3.grid(True)

    plt.tight_layout()
    plt.show()

def scatter_plot_reference_center(enu_list: List[np.ndarray], labels: List[str], filepath: str = None):
    fig, ax = plt.subplots(figsize=(9, 9))
    ax.set_aspect('equal')

    for enu, label in zip(enu_list, labels):
        # Convert the ENU array to a DataFrame
        enu_df = pd.DataFrame(enu, columns=['e', 'n', 'u'])
        
        # Plot the points
        ax.scatter(enu_df['e'], enu_df['n'], label=label, alpha=0.6)

    # Draw concentric circles
    max_distance = np.sqrt((enu_df['e']**2 + enu_df['n']**2).max())
    circle_distances = np.linspace(0, max_distance, num=6)
    
    for distance in circle_distances:
        circle = plt.Circle((0, 0), distance, color='grey', fill=False, linestyle='--', alpha=0.5)
        ax.add_artist(circle)
        ax.text(distance, 0, f'{distance:.1f} m', color='grey', verticalalignment='bottom', horizontalalignment='right')

    # Set the axes and title
    ax.set_title('Scatter Plot with Reference Center')
    ax.set_xlabel('East [m]')
    ax.set_ylabel('North [m]')
    ax.legend()

    # Adjust the axes limits
    ax.set_xlim(-max_distance, max_distance)
    ax.set_ylim(-max_distance, max_distance)

    # Save the plot if a filepath is provided
    if filepath:
        plt.savefig(filepath)

    # Show the plot
    plt.show()

    return fig

def trajectory_plot(enu_list: List[np.ndarray], labels: List[str], filepath: str = None):
    fig, ax = plt.subplots(figsize=(9, 9))
    ax.set_aspect('equal')

    for enu, label in zip(enu_list, labels):
        # Convert the ENU array to a DataFrame
        enu_df = pd.DataFrame(enu, columns=['e', 'n', 'u'])
        
        # Plot the trajectory
        ax.plot(enu_df['e'], enu_df['n'], label=label)

    # Set the axes and title
    ax.set_title('Trajectory Plot with Reference Center')
    ax.set_xlabel('East [m]')
    ax.set_ylabel('North [m]')
    ax.legend()

    # Adjust the axes limits
    ax.axis('equal')

    # Save the plot if a filepath is provided
    if filepath:
        plt.savefig(filepath)

    # Show the plot
    plt.show()

    return fig

def horizontal_error_over_time(enu_list: List[np.ndarray], labels: List[str], filepath: str = None):
    fig, ax = plt.subplots(figsize=(12, 6))

    for enu, label in zip(enu_list, labels):
        # Convert the ENU array to a DataFrame
        enu_df = pd.DataFrame(enu, columns=['e', 'n', 'u'])
        
        # Calculate the horizontal distance
        enu_df['horizontal_error'] = np.sqrt(enu_df['e']**2 + enu_df['n']**2)
        
        # Plot the horizontal error over time
        ax.plot(enu_df.index, enu_df['horizontal_error'], label=label)

    # Set the axes and title
    ax.set_title('Horizontal Error Over Time')
    ax.set_xlabel('Time [s]')
    ax.set_ylabel('Horizontal Error [m]')
    ax.legend()
    ax.grid()

    # Save the plot if a filepath is provided
    if filepath:
        plt.savefig(filepath)

    # Show the plot
    plt.show()

    return fig

def histogram_horizontal_error(enu_list: List[np.ndarray], labels: List[str], bins: int = 30, filepath: str = None):
    fig, ax = plt.subplots(figsize=(12, 6))

    for enu, label in zip(enu_list, labels):
        # Convert the ENU array to a DataFrame
        enu_df = pd.DataFrame(enu, columns=['e', 'n', 'u'])
        
        # Calculate the horizontal distance
        horizontal_error = np.sqrt(enu_df['e']**2 + enu_df['n']**2)
        
        # Plot the histogram of the horizontal error
        ax.hist(horizontal_error, bins=bins, alpha=0.6, label=label)

    # Set the axes and title
    ax.set_title('Histogram of Horizontal Error')
    ax.set_xlabel('Horizontal Error [m]')
    ax.set_ylabel('Frequency')
    ax.legend()

    # Save the plot if a filepath is provided
    if filepath:
        plt.savefig(filepath)

    # Show the plot
    plt.show()

    return fig

def cdf_horizontal_error(enu_list: List[np.ndarray], labels: List[str], filepath: str = None):
    """
    This function calculates and plots the Cumulative Distribution Function (CDF) of horizontal errors.
    The horizontal error is computed as the Euclidean distance in the ENU (East, North, Up) plane. 
    The CDF provides a probability distribution of these errors, indicating the likelihood of an error being 
    less than or equal to a certain value. Horizontal lines at 50%, 95%, and 100% cumulative probabilities 
    are added to the plot for reference.

    Parameters:
    - enu_list: List[np.ndarray] : A list of numpy arrays containing ENU coordinates.
    - labels: List[str] : A list of labels corresponding to each ENU dataset.
    - filepath: str (optional) : The path to save the plot as an image file.
    """
    fig, ax = plt.subplots(figsize=(12, 6))

    for enu, label in zip(enu_list, labels):
        # Convert the ENU array to a DataFrame
        enu_df = pd.DataFrame(enu, columns=['e', 'n', 'u'])
        
        # Calculate the horizontal distance
        horizontal_error = np.sqrt(enu_df['e']**2 + enu_df['n']**2)
        
        # Calculate and plot the CDF of the horizontal error
        sorted_error = np.sort(horizontal_error)
        cdf = np.arange(1, len(sorted_error) + 1) / float(len(sorted_error)) * 100
        ax.plot(sorted_error, cdf, label=label)
    
    # Add horizontal lines at 50%, 95%, and 100%
    ax.axhline(y=50, color='grey', linestyle='--', lw=0.8)
    ax.axhline(y=95, color='grey', linestyle='--', lw=0.8)
    ax.axhline(y=100, color='grey', linestyle='--', lw=0.8)

    # Set the axes and title
    ax.set_title('CDF of Horizontal Error')
    ax.set_xlabel('Horizontal Error [m]')
    ax.set_ylabel('Cumulative Probability [%]')
    ax.set_yticks(np.arange(0, 101, 10))  # Setting y-ticks from 0 to 100 in steps of 10
    ax.legend()

    # Save the plot if a filepath is provided
    if filepath:
        plt.savefig(filepath)

    # Show the plot
    plt.show()

    return fig