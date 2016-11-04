import sys

from scipy.integrate import ode

from dgDynamic.choices import ScipyOdeSolvers, SupportedOdePlugins
from dgDynamic.converters.ode.scipy_converter import get_scipy_lambda
from dgDynamic.plugins.ode_plugin import OdePlugin, OdeOutput, sanity_check, get_initial_values
from dgDynamic.utils.project_utils import LogMixin


class ScipyOde(OdePlugin, LogMixin):
    """
    Scipy ODE solver plugin
    """

    def __init__(self, eq_system=None, integration_range=None, initial_condition=None, delta_t=0.1, parameters=None,
                 solver=ScipyOdeSolvers.VODE, initial_t=0):
        super().__init__(eq_system, integration_range, initial_condition, delta_t=delta_t, parameters=parameters,
                         initial_t=initial_t, ode_solver=solver)

    def __call__(self, integration_range=None, initial_conditions=None, parameters=None, delta_t=0.1, ode_solver=None,
                 **kwargs):
        solver_choice = ode_solver if ode_solver is not None else ScipyOdeSolvers.VODE
        return super().__call__(solver_choice, integration_range, initial_conditions, parameters, delta_t, **kwargs)

    def solve(self, **kwargs) -> OdeOutput:
        self._convert_to_function(get_scipy_lambda)

        if self._user_function is None:
            return None
        if type(self._user_function) is str:
            self._user_function = eval(self._user_function)

        self.logger.debug("Checking scipy parameters...")
        initial_y = get_initial_values(self.initial_conditions, self._symbols)
        sanity_check(self, initial_y)

        self.logger.debug("Started solving using Scipy with method {}".format(self._ode_solver.value))
        self.logger.debug("Initial conditions are {}, \
range: {} and dt: {} ".format(self.initial_conditions, self.integration_range, self.delta_t))

        y_solution = list()
        t_solution = list()
        solver = ode(self._user_function).set_integrator(self._ode_solver.value, **kwargs)
        solver.set_initial_value(y=initial_y, t=self.initial_t)
        solver.t = self.integration_range[0]

        def fixed_step_integration():
            try:
                while solver.successful() and solver.t <= self.integration_range[1]:
                    y_solution.append(solver.y)
                    t_solution.append(solver.t)
                    solver.integrate(solver.t + self.delta_t)
            except SystemError as integration_error:
                self.logger.exception("Integration process failed", integration_error)
                return None

            self.logger.debug("Solving finished using fixed step integration")
            return OdeOutput(solved_by=SupportedOdePlugins.Scipy, dependent=y_solution, independent=t_solution,
                             abstract_system=self._abstract_system, ignore=self._ignored,
                             solver_method=self._ode_solver)

        def variable_step_integration():

            def solution_getter(t, y):
                y_solution.append(y.copy())
                t_solution.append(t)

            solver.set_solout(solout=solution_getter)

            try:
                while solver.successful() and solver.t < self.integration_range[1]:
                    solver.integrate(self.integration_range[1], step=True)
            except SystemError as integration_error:
                self.logger.exception("Integration process failed", integration_error)
                return None

            self.logger.debug("Solving finished using variable step integration")
            return OdeOutput(solved_by=SupportedOdePlugins.Scipy, dependent=y_solution, independent=t_solution,
                             abstract_system=self._abstract_system, ignore=self._ignored,
                             solver_method=self._ode_solver)

        if self._ode_solver is ScipyOdeSolvers.DOP853 or self._ode_solver is ScipyOdeSolvers.DOPRI5:
            return variable_step_integration()
        else:
            return fixed_step_integration()


if __name__ == "__main__":
    print("Plugin not meant as standalone application", file=sys.stderr)
