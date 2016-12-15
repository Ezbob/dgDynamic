from abc import abstractmethod, ABC
from ..plugin_base import PluginBase
import dgDynamic.utils.typehints as th
import typing as tp


class OdePlugin(PluginBase, ABC):
    """
    Super class for all the ODE plugins. This class inherits the Abstract Base Class and functions as a
    interface for all the ODE plugins.
    """

    def simulate(self, simulation_range, initial_conditions, rate_parameters, drain_parameters, *args, **kwargs):
        pass

    def __init__(self, simulator, delta_t: tp.Optional[float]=0.1, initial_t: th.Real=0,
                 intergrator_mode: tp.Optional[tp.Union[str, th.Enum]]=None):
        super().__init__()
        self._simulator = simulator
        self.initial_t = initial_t
        self.intergrator_mode = intergrator_mode
        self.delta_t = delta_t
