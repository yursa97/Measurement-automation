from lib2.VNATimeResolvedDispersiveMeasurement2D import *

class VacuumRabiOscillations2D(VNATimeResolvedDispersiveMeasurement2D):

    def __init__(self, name, sample_name, line_attenuation_db = 60,
        plot_update_interval=1, **devs_aliases_map):
        super().__init__(name, sample_name, devs_aliases_map)
        self._measurement_result = VacuumRabiOscillations2DResult(name,
                    sample_name)
        self._sequence_generator =\
                        IQPulseBuilder.build_vacuum_rabi_oscillations_sequences


    def set_fixed_parameters(self, vna_parameters, excitation_frequency,
        ro_awg_parameters, q_awg_parameters, q_z_awg_params,
        pulse_sequence_parameters):

        q_if_frequency = q_awg_parameters["calibration"] \
            .get_radiation_parameters()["if_frequency"]
        q_lo_parameters = {"frequency":excitation_frequency+q_if_frequency}

        super().set_fixed_parameters(vna_parameters, q_lo_parameters,
            ro_awg_parameters, q_awg_parameters,
            pulse_sequence_parameters, q_z_awg_params=q_z_awg_params)

    def set_swept_parameters(self, z_pulse_offset_voltages, interaction_durations):
        q_if_frequency = self._q_awg.get_calibration() \
            .get_radiation_parameters()["if_frequency"]
        swept_pars = {"z_pulse_offset_voltage":\
                        (self._set_z_pulse_offset_voltage,
                            z_pulse_offset_voltages),
                      "interaction_duration":
                        (self._set_interaction_duration_and_output,
                        interaction_durations)}
        super().set_swept_parameters(**swept_pars)

    def _set_z_pulse_offset_voltage(self, z_pulse_offset_voltage):
        self._pulse_sequence_parameters["z_pulse_offset_voltage"] =\
                z_pulse_offset_voltage

    def _set_interaction_duration_and_output(self, interaction_duration):

        self._pulse_sequence_parameters["interaction_duration"]=\
                interaction_duration
        self._output_pulse_sequence()

class VacuumRabiOscillations2DResult(VNATimeResolvedDispersiveMeasurement2DResult):

    def _prepare_data_for_plot(self, data):
        return  data["interaction_duration"]/1e3,\
                data["z_pulse_offset_voltage"],\
                data["data"]

    def _annotate_axes(self, axes):
        x_label = "Interaction duration [$\mu$s]"
        axes[-1].set_xlabel(x_label)
        axes[-2].set_xlabel(x_label)
        y_label = "Z-pulse offset voltage [V]"
        axes[0].set_ylabel(y_label)
        axes[-2].set_ylabel(y_label)
