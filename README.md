# EE662Fall2021

WsnLab.py is a simulation library in Python based on WsnSimPy for self-organized networks.

# Requirements

You need to install the following packages.
- simpy


Source Files for Simulation:
- Baseline: wsnlab/data_collection_tree.py
- Midterm 2 Implementation: wsnlab/variable_tx_range_w_routers.py

The implementation names variable tx range, but this is a configurable toggle.

Configurable Toggles:
- VIS: 0 or 1, 0 for no visualization, 1 for visualization of packet traces
- ALLOW_TX_POWER_CHOICE: 0 or 1, 0 for default max tx power for all nodes, 1 smart choice protocol