import sys, os, copy, time, warnings
sys.path.append('../lib/')
import numpy as np
import lib_material, lib_excel, obj_unit_cell, IO_util, cal_band, cal_RGF
import traceback
from multiprocessing import Pool

if __name__ == '__main__':
    try:
        from PyQt4 import QtGui
        app = QtGui.QApplication(sys.argv)
    except:
        warnings.warn('No valid PyQt4 installed. This may cause error!')
    '''
    This program simulates ballistic transpotation along x-axis.
    '''
    t_start = time.time()       # record import time
    inputs = IO_util.importFromExcel('../input/RGF_input_file.xlsx')
    t_import = time.time() - t_start
    print('Import time:', t_import, '(sec)')
    '''
    Create unit cell
    '''
    t_start = time.time()       # record unit cell generation time
    unit_list = []              # unit cell object list
    for idx in range(len(inputs['Unit cell'])):
        new_unitcell = obj_unit_cell.UnitCell(inputs, idx)
        new_unitcell.genHamiltonian()
        unit_list.append(new_unitcell)
        IO_util.saveAsExcel(inputs, idx, new_unitcell, save_type='matrix')
    t_unitGen = time.time() - t_start
    print('Generate unit cell time:',t_unitGen,'(sec)')
    '''
    Calculate band structure
    '''
    t_start = time.time()       # record band structure time
    #bs_parser = bs_GPU.BandStructure(inputs)
    if inputs['function']['isPlotBand']:
        for u_idx, unit in enumerate(unit_list):
            band_parser = cal_band.CPU(inputs, unit)
            bandgap_list = {'x':[],'y':[]}
            # construct each unit cell
            for idx in range(0,inputs['kx_mesh'],int(inputs['kx_mesh']/500)):
                if inputs['GPU']['enable']:
                    val, vec = bs_parser.calState_GPU(unit, idx)
                else:
                    val, vec = band_parser.calState(idx)
                ## record data ##
                bandgap_list['x'].append(unit.kx_norm)
                bandgap_list['y'].append(val)
            IO_util.saveAsFigure(inputs, u_idx, unit, bandgap_list, save_type='band')
    t_band = time.time() - t_start
    print('Calculate band structure:',t_band,'(sec)')
    '''
    Construct Green's matrix
    '''
    t_start = time.time()
    RGF_util = cal_RGF.CPU(inputs, unit_list)
    
    kx_sweep = range(inputs['mesh'][0],inputs['mesh'][1])
    RGF_result = {'E':[],'T':[],'R':[]}
    if True:
        with Pool(processes=2) as mp:
            RGF_output = mp.map(RGF_util.calRGF_transmit,kx_sweep)
        RGF_result['E'] = np.array(RGF_output)[:,0]
        RGF_result['T'] = np.array(RGF_output)[:,1]
        RGF_result['R'] = np.array(RGF_output)[:,2]
    else:
        for kx_idx in range(inputs['mesh'][0],inputs['mesh'][1]):        # sweep kx meshing
            if inputs['GPU']['enable']:
                ## RGF
                RGF_util.calRGFT_GPU(kx_idx, CB_idx)
                #RGF_util.calRGFR_GPU(kx_idx, CB_idx)
                ## Jt/JR
                Jt, Jr = RGF_util.calTR_GPU()
            else:
                ## RGF
                RGF_output = RGF_util.calRGF_transmit(kx_idx)
            RGF_result['E'].append(RGF_output[0])
            RGF_result['T'].append(RGF_output[1])
            RGF_result['R'].append(RGF_output[2])
    ## plot transmission ##
    unit = unit_list[0]
    IO_util.saveAsFigure(inputs, -1, unit, RGF_result, save_type='TR')
    IO_util.saveAsExcel(inputs, -1, unit, RGF_result, save_type='TR')
    t_RGF = time.time() - t_start
    print('Calculate RGF:',t_RGF,'(sec)')