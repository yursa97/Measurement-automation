
from lib2.VNATimeResolvedDispersiveMeasurement2D import *

class DispersiveRabiChevrons(VNATimeResolvedDispersiveMeasurement2D):

    def __init__(self, name, sample_name, **devs_aliases_map):
        devs_aliases_map["q_z_awg"] = None
        super().__init__(name, sample_name, devs_aliases_map)
        self._measurement_result = DispersiveRabiChevronsResult(name, sample_name)
        self._sequence_generator = IQPulseBuilder.build_dispersive_rabi_sequences

    def set_fixed_parameters(self, vna_parameters,
        ro_awg_parameters, q_awg_parameters, pulse_sequence_parameters):
        super().set_fixed_parameters(vna_parameters, {},
            ro_awg_parameters, q_awg_parameters, pulse_sequence_parameters)

    def set_swept_parameters(self, excitation_durations, excitation_freqs):
        q_if_frequency = self._q_awg.get_calibration() \
            .get_radiation_parameters()["if_frequency"]
        swept_pars = {"excitation_duration":\
                        (self._output_pulse_sequence,
                            excitation_durations),
                      "excitation_frequency":
                        (lambda x: self._q_lo.set_frequency(x+q_if_frequency),
                            excitation_freqs)}
        super().set_swept_parameters(**swept_pars)

    def _output_pulse_sequence(self, excitation_duration):
        self._pulse_sequence_parameters["excitation_duration"] =\
                                                            excitation_duration
        super()._output_pulse_sequence()

class DispersiveRabiChevronsResult(VNATimeResolvedDispersiveMeasurement2DResult):

    def _prepare_data_for_plot(self, data):
        return data["excitation_frequency"]/1e9,\
                data["excitation_duration"]/1e3,\
                data["data"]

    def _annotate_axes(self, axes):
        axes[0].set_ylabel("Excitation duration [$\mu$s]")
        axes[-2].set_ylabel("Excitation duration [$\mu$s]")
        axes[-1].set_xlabel("Excitation frequency [GHz]")
        axes[-2].set_xlabel("Excitation frequency [GHz]")
