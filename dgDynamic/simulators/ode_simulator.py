import functools as ft
import sympy as sp
from collections import OrderedDict
from typing import Union
from dgDynamic.choices import SupportedOdePlugins
from .simulator import DynamicSimulator


class ODESystem(DynamicSimulator):
    """
    This class is meant to create ODEs in SymPys abstract symbolic mathematical syntax, using deviation graphs
    from the MØD framework.
    """
    def __init__(self, graph):
        super().__init__(graph=graph)
        # the mass action law parameters. For mathematical reasons the symbol indices start at 1
        self.parameters = OrderedDict((edge.id, sp.Symbol("k{}".format(index + 1)))
                                      for index, edge in enumerate(self.graph.edges))

    def get_plugin_from_enum(self, enum_variable, *args, **kwargs):
        if enum_variable == SupportedOdePlugins.SciPy:
            from dgDynamic.plugins.ode.scipy import ScipyOde
            return ScipyOde(self, *args, **kwargs)
        elif enum_variable == SupportedOdePlugins.MATLAB:
            from dgDynamic.plugins.ode.matlab import MatlabOde
            return MatlabOde(self, *args, **kwargs)

    def get_plugin(self, plugin_name: Union[str, SupportedOdePlugins], *args, **kwargs):
        if isinstance(plugin_name, str):
            for plugin in SupportedOdePlugins:
                if plugin.value.strip().lower() == plugin_name.strip().lower():
                    return self.get_plugin_from_enum(plugin, *args, **kwargs)
            raise ValueError("plugin name not recognized")
        elif isinstance(plugin_name, SupportedOdePlugins):
            return self.get_plugin_from_enum(plugin_name, *args, **kwargs)

    def generate_rate_laws(self):
        for edge in self.graph.edges:
            reduce_me = (sp.Symbol(vertex.graph.name) for vertex in edge.sources)
            reduced = ft.reduce(lambda a, b: a * b, reduce_me)
            yield self.parameters[edge.id] * reduced

    def generate_equations(self):
        """
        This function will attempt to create the symbolic ODEs using the rate laws.
        """
        ignore_dict = dict(self.ignored)
        for vertex in self.graph.vertices:
            if vertex.graph.name in ignore_dict:
                yield vertex.graph.name, 0
            else:
                # Since we use numpy, we can use the left hand expresses as mathematical expressions
                equation_result = 0
                for reaction_edge, lhs in zip(self.graph.edges, self.generate_rate_laws()):
                    for source_vertex in reaction_edge.sources:
                        if vertex.id == source_vertex.id:
                            equation_result -= lhs
                    for target_vertex in reaction_edge.targets:
                        if vertex.id == target_vertex.id:
                            equation_result += lhs

                yield vertex.graph.name, equation_result

    def __repr__(self):
        return "<Abstract Ode Simulator>"

