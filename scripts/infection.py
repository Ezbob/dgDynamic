"""
Infection model
This model, models the relationship between the
(I)fected, (R)ecovered and the (S)usceptible under the outbreak of some decease.
The recovered becomes immune to the infected once they recover,
and the model starts out with some infected.
"""
import mod
from dgDynamic.mod_dynamics import dgDynamicSim
from dgDynamic.choices import MatlabOdeSolvers
import numpy as np

susceptible_infected = "S + I -> 2 I\n"
recovered = "I -> R\n"
infected_stays_infected = "2 I -> 2 I\n"
recovered_stays_recovered = "R + I -> R + I\n"

whole_model = susceptible_infected + recovered + infected_stays_infected + recovered_stays_recovered

dg = mod.dgAbstract(
    whole_model
)

initial_conditions = {
    'S': 200,
    'I': 1,
}

parameters = {
    susceptible_infected: 0.001,
    infected_stays_infected: 0.001,
    recovered_stays_recovered: 0.001,
    recovered: 0.03,
}

integration_range = (0, 200)

ode = dgDynamicSim(dg, simulator_choice="ODE")

# Name of the data set
name = "infected"
# figure_size in centimetres
figure_size = (40, 20)

with ode("scipy") as scipy:
    # Let's generate some sample delta_ts
    for delta_t in np.linspace(1, 0.01, num=5):
        scipy(integration_range, initial_conditions, parameters, delta_t=delta_t).plot(figure_size=figure_size)

with ode("Matlab") as matlab:
    for supported in MatlabOdeSolvers:
        matlab(integration_range, initial_conditions, parameters, supported).plot(figure_size=figure_size)
