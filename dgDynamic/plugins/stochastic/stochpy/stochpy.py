import contextlib as cl
import enum
import io
import tempfile
import time
import warnings
import dgDynamic.base_converters.convert_base as converter_base
import dgDynamic.output as o
from collections import defaultdict
import dgDynamic.plugins.stochastic.stochpy.stochpy_converter as stochpy_converter
import dgDynamic.utils.messages as messages
from dgDynamic.choices import SupportedStochasticPlugins, StochPyStochasticSolvers
from dgDynamic.config.settings import logging_is_enabled
from dgDynamic.plugins.stochastic.stochastic_plugin import StochasticPlugin

name = SupportedStochasticPlugins.StochPy


class StochPyStochastic(StochasticPlugin):

    def __init__(self, simulator, stochastic_method=StochPyStochasticSolvers.direct, timeout=None):
        super().__init__()
        self._method = stochastic_method
        self.timeout = timeout
        self._simulator = simulator

    def generate_psc_file(self, writable_stream, rate_law_dict, initial_conditions,
                          rate_parameters, drain_parameters=None, translate_dict=None):

        internal_symbols = self._simulator.internal_symbol_dict
        internal_drains = self._simulator.internal_drain_dict

        rates = dict(converter_base.get_edge_rate_dict(self._simulator.graph, rate_parameters,
                                                       self._simulator.parameters))
        for sym in self._simulator.parameters.values():
            # adding in any missing parameter values
            new_sym = sym.replace('$', '')
            if new_sym not in rates:
                rates[new_sym] = 0

        writable_stream.write(stochpy_converter.generate_fixed_species(self._simulator.ignored, internal_symbols))

        writable_stream.write(stochpy_converter.generate_reactions(rate_law_dict, translate_dict))

        drain_values = dict(converter_base.get_drain_rate_dict(internal_drains, drain_parameters))

        writable_stream.write(stochpy_converter.generate_drains(drain_values, internal_drains, internal_symbols))

        writable_stream.write('\n')
        writable_stream.write(stochpy_converter.generate_rates(rates))
        writable_stream.write("\n")
        initial_values = dict(zip((sym.replace('$', '') for sym in self._simulator.symbols_internal),
                                  converter_base.get_initial_values(initial_conditions, self._simulator.symbols)))
        writable_stream.write(stochpy_converter.generate_initial_conditions(initial_values))
        writable_stream.write("\n")

    @property
    def method(self):
        if isinstance(self._method, enum.Enum):
            return self._method
        elif isinstance(self._method, str):
            for supported in StochPyStochasticSolvers:
                name, value = supported.name.lower().strip(), supported.value.lower().strip()
                user_method = self._method.lower().strip()
                if user_method == name or user_method == value:
                    return supported

    @method.setter
    def method(self, value):
        self._method = value

    def simulate(self, simulation_range, initial_conditions,
                 rate_parameters, drain_parameters=None, *args, **kwargs):

        def choose_method_and_run():

            if self.method == StochPyStochasticSolvers.direct:
                stochpy_module.Method('Direct')
            elif self.method == StochPyStochasticSolvers.tauLeaping:
                stochpy_module.Method('TauLeaping')

            self.logger.info("simulation method name: {}".format(stochpy_module.sim_method_name))
            stochpy_module.Endtime(simulation_range[1])
            self.logger.info("simulation end time: {}".format(stochpy_module.sim_end))

            self.logger.info("Running simulation...")
            start_time = time.time()
            try:
                with warnings.catch_warnings():
                    warnings.filterwarnings('ignore')
                    stdout_str = io.StringIO()
                    with cl.redirect_stdout(stdout_str):
                        stochpy_module.DoStochSim()
                    self.logger.info(stdout_str.getvalue())
            except BaseException as exception:
                if logging_is_enabled():
                    self.logger.error("Exception in stochpy simulation: {}".format(str(exception)))
                messages.print_solver_done(name, self.method.name, was_failure=True)
                return o.SimulationOutput(name, simulation_range, self._simulator.symbols,
                                          solver_method=self.method, errors=(exception,))
            finally:
                stdout_str.close()
            end_time = time.time()
            self.logger.info("Simulation ended. Execution time: {} secs".format(end_time - start_time))
            data = stochpy_module.data_stochsim.getSpecies()
            messages.print_solver_done(name, method_name=self.method.name)
            return o.SimulationOutput(name, simulation_range, self._simulator.symbols,
                                      independent=data[:, :1], dependent=data[:, 1:])

        with tempfile.TemporaryDirectory() as tmp:
            stdout_str = io.StringIO()
            model_file_path = "{}/model.psc".format(tmp)
            with open(model_file_path, mode="w+") as file_stream:
                rate_law_dict = dict(zip(self._simulator.abstract_edges,
                                         self._simulator.generate_propensities()))
                self.generate_psc_file(file_stream, rate_law_dict, initial_conditions, rate_parameters,
                                       drain_parameters, self._simulator.internal_symbol_dict)
                file_stream.seek(0)
                self.logger.info("StochPy simulation file:\n{}".format("".join(file_stream.readlines())))

            with cl.redirect_stdout(stdout_str):
                import stochpy as sp
                stochpy_module = sp.SSA(dir=tmp, model_file="model.psc")

            output = choose_method_and_run()

        return output
