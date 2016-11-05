import functools as ft
import sympy as sp
from collections import OrderedDict
from typing import Union
from dgDynamic.choices import SupportedOdePlugins
from dgDynamic.utils.project_utils import ProjectTypeHints
from .simulator import DynamicSimulator


class ODESystem(DynamicSimulator):
    """
    This class is meant to create ODEs in SymPys abstract symbolic mathematical syntax, using deviation graphs
    from the MØD framework.
    """
    def __init__(self, graph):
        """
        The initialisation phase consist of creating Sympy Symbols for the vertices of the deviation graph,
        and creating the rate laws for each reaction.
        :param graph: if this is parsed as a string the init function will try and parse the string argument to
        dgAbstract, else it just gets stored.
        """
        super().__init__(graph=graph)
        self.flux_terms = dict()

        # every vertex in the deviation graph gets a mapping from it's id to the corresponding SymPy Symbol
        self.symbols = OrderedDict(((vertex.id, sp.Symbol(vertex.graph.name)) for vertex in self.graph.vertices))

        # the mass action law parameters. For mathematical reasons the symbol indices start at 1
        self.parameters = OrderedDict((edge.id, sp.Symbol("k{}".format(index + 1)))
                                      for index, edge in enumerate(self.graph.edges))

    def get_plugin_from_enum(self, enum_variable, *args, **kwargs):
        if enum_variable == SupportedOdePlugins.Scipy:
            from dgDynamic.plugins.ode.scipy import ScipyOde
            return ScipyOde(self, *args, **kwargs)
        elif enum_variable == SupportedOdePlugins.Matlab:
            from dgDynamic.plugins.ode.matlab import MatlabOde
            return MatlabOde(self, *args, **kwargs)

    def get_plugin(self, plugin_name: Union[str, SupportedOdePlugins], *args, **kwargs):
        if isinstance(plugin_name, str):
            for plugin in SupportedOdePlugins:
                if plugin.value in plugin_name.lower():
                    return self.get_plugin_from_enum(plugin, *args, **kwargs)
            raise ValueError("plugin name not recognized")
        elif isinstance(plugin_name, SupportedOdePlugins):
            return self.get_plugin_from_enum(plugin_name, *args, **kwargs)

    def generate_rate_laws(self):
        for index, edge in enumerate(self.graph.edges):
            reduce_me = (self.symbols[vertex.id] for vertex in edge.sources)
            reduced = ft.reduce(lambda a, b: a * b, reduce_me)
            yield self.parameters[edge.id] * reduced

    def generate_equations(self):
        """
        This function will attempt to create the symbolic ODEs using the rate laws.
        :return: a tuple of tuples, wherein each nested tuple is a two-tuple consisting of the vertex id, of which the
        change over time is subjective to, and the symbolic ODE.
        """
        left_hand_sides = tuple(self.generate_rate_laws())
        ignore_dict = dict(self.ignored)
        for vertex_id, vertex in enumerate(self.graph.vertices):
            if sp.Symbol(vertex.graph.name) in ignore_dict:
                yield vertex.graph.name, 0
            else:
                # Since we use numpy, we can use the left hand expresses as mathematical expressions
                sub_result = 0
                for reaction_index, reaction_edge in enumerate(self.graph.edges):
                    for source_vertex in reaction_edge.sources:
                        if vertex.id == source_vertex.id:
                            sub_result -= left_hand_sides[reaction_index]

                    for target_vertex in reaction_edge.targets:
                        if vertex.id == target_vertex.id:
                            sub_result += left_hand_sides[reaction_index]

                if vertex.graph.name in self.flux_terms:
                    sub_result += self.flux_terms[vertex.graph.name]

                yield vertex.graph.name, sub_result

    def add_terms(self, flux_terms: dict):
        for key, val in flux_terms.items():
            if not isinstance(key, (str,) + tuple(sp.core.all_classes)):
                raise TypeError("Expected string or sympy expression for key: {}", key)
            if isinstance(val, str):
                self.flux_terms[key] = sp.sympify(val)
            elif isinstance(val, tuple(sp.core.all_classes)):
                self.flux_terms[key] = val
            else:
                raise TypeError("Expected values to be a string or a sympy expression")

        return self

    def unchanging_species(self, *species: Union[str, sp.Symbol, ProjectTypeHints.Countable_Sequence]):
        if len(self.ignored) < self.species_count:
            if isinstance(species, str):
                self.ignored = tuple((item, index) for index, item in enumerate(self.symbols.values())
                                     if sp.Symbol(species) == item)
            elif isinstance(species, sp.Symbol):
                self.ignored = tuple((item, index) for index, item in enumerate(self.symbols.values())
                                     if species == item)
            else:
                self.ignored = tuple((item, index) for index, item in enumerate(self.symbols.values())
                                     for element in species if sp.Symbol(element) == item)
        else:
            self.logger.warn("ignored species count exceeds the count of actual species")
        return self

    def __repr__(self):
        return "<Abstract Ode System {}>".format(self.left_hand_sides)

