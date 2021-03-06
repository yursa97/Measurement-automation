
from matplotlib import pyplot as plt
from scipy import *
import numpy as np
from scipy.signal import *
from scipy.optimize import *
from IPython.display import clear_output
from lib2.fulaut.qubit_spectra import *

class SpectrumOracle():

    '''
    This class automatically processes spectral data for different types of qubits
    '''

    qubit_spectra = {"transmon":transmon_spectrum}

    def __init__(self, qubit_type, tts_result, initial_guess_qubit_params):
        '''
        parameter_period_grid = grids[0]
        parameter_at_sweet_spot_grid = grids[1]
        frequency_grid = grids[2]
        d_grid = grids[3]
        alpha_grid = grids[4]
        '''
        self._tts_result = tts_result
        self._qubit_spectrum = SpectrumOracle.qubit_spectra[qubit_type]

        self._y_scan_area_size = 50e-3
        period, sweet_spot_cur, q_freq, d = initial_guess_qubit_params
        q_freq = q_freq/1e9

        fl_grid = 0.98*period, 1.02*period, 3
        sws_grid = sweet_spot_cur-0.02*period, sweet_spot_cur+0.02*period, 5
        freq_grid = q_freq*0.7, q_freq*1.3, 50
        d_grid = d*0.9, d*1.1, 5
        alpha_grid = 100e-3, 120e-3, 5

        slices = []
        self._grids = (fl_grid, sws_grid, freq_grid, d_grid, alpha_grid)
        for grid in self._grids:
            step = (grid[1]-grid[0])/grid[2]
            slices.append(slice(grid[0], grid[1], step))

        self._p0 = [(grid[0]+grid[1])/2 for grid in self._grids]
        self._slices = slices


    def launch(self, plot=False):


        self._extract_data(plot=plot)

        self._counter = 0
        self._iterations = self._grids[2][2]*self._grids[3][2]

        freq_slice = self._slices[2]
        d_slice = self._slices[3]
        opt_params_coarse = brute(self._cost_function_coarse, (freq_slice, d_slice),
                                args = (self._y_scan_area_size*2, self._points),
                                                                full_output=False)
        opt_params_coarse = self._p0[:2]+list(opt_params_coarse)
        if plot:
            plt.figure()
            plt.plot(self._points[:,0], self._points[:,1], ".")
            plt.plot(self._parameter_values,
                    self._qubit_spectrum(self._parameter_values, *opt_params_coarse), ":")

        fine_period_grid = 0.95*self._p0[0], 1.05*self._p0[0]
        fine_sws_grid = self._p0[1]-0.01*self._p0[0], self._p0[1]+0.01*self._p0[0]
        fine_freq_grid = opt_params_coarse[2]*0.975, opt_params_coarse[2]*1.025
        fine_d_grid = opt_params_coarse[3]*0.95, opt_params_coarse[3]*1.05
        fine_alpha_grid = self._slices[-1]
        Ns = 5
        self._counter = 0
        self._iterations = Ns**4*self._grids[-1][2]

        opt_params = brute(self._cost_function_fine, (fine_period_grid,
                                                     fine_sws_grid,
                                                     fine_freq_grid,
                                                     fine_d_grid,
                                                     fine_alpha_grid),
            args = (self._y_scan_area_size, self._points), Ns=Ns, full_output=False)

        if plot:
            plt.plot(self._parameter_values,
                        self._qubit_spectrum(self._parameter_values,
                                            *opt_params[:-1]))
            plt.plot(self._parameter_values,
                        self._qubit_spectrum(self._parameter_values,
                                            *opt_params[:-1])-opt_params[-1])
            plt.plot(self._parameter_values,
                        self._qubit_spectrum(self._parameter_values,
                                            *opt_params[:-1])-2*opt_params[-1])
            plt.gcf().set_size_inches(15,5)

        opt_params[2] = opt_params[2]*1e9
        return opt_params


    def _extract_data(self, plot=False):
        try:
            parameter_name = self._tts_result._parameter_names[0]
        except:
            parameter_name = "Current [A]"
        data = self._tts_result.get_data()
        self._parameter_values = data[parameter_name]
        try:
            self._freqs = data["Frequency [Hz]"][:]/1e9
        except:
            self._freqs = data["frequency"][:]/1e9
        self._Z = (data["data"].T - data["data"][:, -1]).T

        points = []
        for idx in range(len(self._parameter_values)):
            row = abs(abs(self._Z))[idx]
            extrema_idcs = array(argrelextrema(row, np.greater, order=2))[0]
            threshold = 0.1
            bright_extrema = extrema_idcs

            condition1 = row[extrema_idcs]>median(row)+0.05*ptp(abs(self._Z))
            while len(bright_extrema)>5:
                condition2 = row[extrema_idcs]>threshold*np.max(abs(self._Z))
                bright_extrema = extrema_idcs[np.logical_and(condition1, condition2)]
                threshold+=0.01
            points += list(zip([self._parameter_values[idx]]*len(bright_extrema),
                            self._freqs[bright_extrema]))

        self._points = array(points)

        if plot:
            x = self._parameter_values
            freqs = self._freqs
            x_plot = concatenate((x-(x[1]-x[0])/2, x[-1:]+(x[1]-x[0])/2))
            freqs_plot = concatenate((freqs-(freqs[1]-freqs[0])/2,
                                            freqs[-1:]+(freqs[1]-freqs[0])/2))

            plt.pcolormesh(x_plot, freqs_plot, abs(self._Z).T)
            plt.plot()
            plt.plot(self._points[:,0], self._points[:,1], 'r.')
            plt.colorbar()
            plt.gcf().set_size_inches(15,5)


    def _cost_function_coarse(self, params, y_scan_area_size, points, verbose=False):
        clear_output(wait=True)
        percentage_done = self._counter/self._iterations*100
        if percentage_done <= 100:
            print("\rDone: %.2f%%, %.d/%d"%(percentage_done, self._counter, self._iterations), end="")
            print(", ["+(("{:.2e}, "*len(params))[:-2]).format(*params)+"]", end="")
#             sleep(0.1)
        else:
            print("\rDone: 100%, polishing...", end="")
            print(", params:", params, end="")
#             sleep(0.1)
        self._counter += 1
#         print(params)
        q_freq = params[0]
        params = self._p0[:2]+list(params)

        distances = abs(self._qubit_spectrum(points[:,0], *params)-points[:,1])
        chosen = distances<y_scan_area_size
        distances_chosen = distances[chosen]
        chosen_points = points[chosen]

        d = params[3]
        if len(chosen_points)<len(self._parameter_values)/3 or d>0.95:
            loss_value = sum(distances)**2
        else:
            loss_value = distances_chosen.sum()/(len(chosen_points)+1)**2
        if verbose:
            return loss_value, chosen_points
        print(", loss:", "%.2e"%loss_value, ", chosen points:", len(chosen_points))
        return loss_value

    def _cost_function_fine(self, params, y_scan_area_size, points, verbose=False):
        x_coords = sorted(set(points[:,0]))

        loss = []
        loss2 = []
        loss3 = []
        chosen_points = []
        chosen_points2 = []
        chosen_points3 = []

        total_distance_of_the_main_line_from_points = 0

        for x_coord in x_coords:
            same_x_points = points[points[:,0]==x_coord]
            distances = abs(self._qubit_spectrum(x_coord, *params[:4])-same_x_points[:,1])
            distances2 = abs(self._qubit_spectrum(x_coord, *params[:4])-params[-1]-same_x_points[:,1])
            distances3 = abs(self._qubit_spectrum(x_coord, *params[:4])-2*params[-1]-same_x_points[:,1])
            total_distance_of_the_main_line_from_points += sum(distances)

            min_arg = argmin(distances)
            min_arg_2 = argmin(distances2)
            min_arg_3 = argmin(distances3)
            min_dist = distances[min_arg]
            min_dist_2 = distances2[min_arg_2]
            min_dist_3 = distances3[min_arg_3]

            if min_dist<y_scan_area_size:
                loss.append(min_dist)
                if verbose:
                    chosen_points.append((x_coord, same_x_points[min_arg,1]))
            if min_dist_2<y_scan_area_size:
                loss2.append(min_dist_2)
                if verbose:
                    chosen_points2.append((x_coord, same_x_points[min_arg_2,1]))
            if min_dist_3<y_scan_area_size:
                loss3.append(min_dist_3)
                if verbose:
                    chosen_points3.append((x_coord, same_x_points[min_arg_3,1]))

        total_chosen_points = (len(loss)+len(loss2)+len(loss3))

        if len(loss)<len(x_coords)/3:
            loss_value = total_distance_of_the_main_line_from_points**2
        else:
            loss_value = sum(array(loss))/(len(loss)+1)+\
                            0.1*sum(array(loss2))/(len(loss2)+1)+\
                                0.01*sum(array(loss3))/(len(loss3)+1)
            loss_value /= total_chosen_points**2

        if self._counter%1==0:
            percentage_done = self._counter/self._iterations*100
            clear_output(wait=True)
            print("\rDone: %.2f%%, %.d/%d"%(percentage_done, self._counter, self._iterations), end="")
            print(", ["+(("{:.2e}, "*len(params))[:-2]).format(*params)+"]", end="")
            print(", loss:", "%.2e"%loss_value, ", chosen points:", (total_chosen_points))
        self._counter += 1

        if verbose:
            return loss_value, chosen_points, chosen_points2, chosen_points3
        return loss_value
