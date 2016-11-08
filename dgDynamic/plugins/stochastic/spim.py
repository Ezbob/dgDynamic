import os.path
import os
import array
import csv
import subprocess
import tempfile
from dgDynamic.config.settings import config
from io import StringIO
from dgDynamic.config.settings import config
from .stochastic_plugin import StochasticPlugin, SimulationOutput
from ...converters.stochastic.spim_converter import generate_initial_values, generate_rates, generate_automata_code, \
    generate_preamble
from dgDynamic.choices import SupportedStochasticPlugins


class SpimStochastic(StochasticPlugin):

    def __init__(self, simulator, sample_range=None, parameters=None, initial_conditions=None,):
        sample_range = sample_range if sample_range is None else (float(sample_range[0]), sample_range[1])
        super().__init__(sample_range=sample_range, parameters=parameters, initial_conditions=initial_conditions)
        self._spim_path = config['Simulation']['SPIM_PATH']
        if self._spim_path is None or not self._spim_path:
            self._spim_path = os.path.join(os.path.dirname(__file__), "spim.ocaml")
        self._spim_path = os.path.abspath(self._spim_path)
        self._simulator = simulator
        self._ocamlrun_path = os.path.abspath(config['Simulation']['OCAML_RUN'])

    def solve(self) -> SimulationOutput:
        self.sample_range = self.sample_range if self.sample_range is None else \
            (float(self.sample_range[0]), self.sample_range[1])

        def generate_code_file(file_path):
            with open(file_path, mode="w") as code_file:
                code_file.write(generate_preamble(self.sample_range, symbols=self._simulator.symbols,
                                                  ignored=self._simulator.ignored))
                code_file.write('\n')
                code_file.write(generate_rates(self._simulator, channel_dict=channels, parameters=self.parameters))
                code_file.write('\n')
                code_file.write(generate_automata_code(channels, self._simulator.symbols))
                code_file.write('\n\n')
                code_file.write(generate_initial_values(self._simulator.symbols, self.initial_conditions))

        if self.parameters is None or self.initial_conditions is None:
            raise ValueError("Missing parameters or initial values")

        with tempfile.TemporaryDirectory() as tmpdir:
            channels = self._simulator.generate_channels()

            file_path_code = os.path.join(tmpdir, "spim.spi")
            generate_code_file(file_path_code)

            if bool(config['Logging']['ENABLE_LOGGING']):
                with open(file_path_code) as debug_file:
                    self.logger.info("SPiM simulation file:\n{}".format(debug_file.read()))

            run_parameters = (self._ocamlrun_path, self._spim_path, file_path_code)
            stdout = subprocess.check_output(run_parameters)
            self.logger.info("SPiM stdout:\n".format(stdout))

            csv_file_path = os.path.join(tmpdir, "spim.spi.csv")
            if not os.path.isfile(csv_file_path):
                raise IOError("Missing SPiM output")

            with open(csv_file_path) as file:
                reader = csv.reader(file)
                next(reader)
                independent = array.array('d')
                dependent = []
                for line in reader:
                    independent.append(float(line[0]))
                    dependent.append(array.array('d', map(float, line[1:])))

        return SimulationOutput(SupportedStochasticPlugins.SPiM, dependent=dependent, independent=independent,
                                abstract_system=self._simulator)
