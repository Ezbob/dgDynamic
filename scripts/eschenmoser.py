from dgDynamic import dgDynamicSim, HyperGraph, show_plots
import matplotlib.pyplot as plt
import numpy as np
from dgDynamic.analytics import DynamicAnalysisDevice
import random
import enum
import csv

runs = 10000


class ImportantSpecies(enum.Enum):
    HCN = "HCN"
    Glyoxylate = "Glyoxylate"
    Oxaloglycolate = "Oxaloglycolate"
    Oxoaspartate = "Oxoaspartate"


cycle1_reactions = [
    "2 {} -> C1S1".format(ImportantSpecies.HCN.name),
    "C1S1 -> C1S2",
    "C1S2 + {} -> C1S3".format(ImportantSpecies.Glyoxylate.name),
    "C1S3 -> C1S4",
    "C1S4 -> C1S5",
    "C1S5 -> C1S6 + {}".format(ImportantSpecies.Glyoxylate.name),
    "C1S6 -> {}".format(ImportantSpecies.Glyoxylate.name),
]

cycle2_reactions = [
    "C2S10 + {} -> C2S1".format(ImportantSpecies.Glyoxylate.name),
    "C2S1 -> C2S2",
    "C2S2 -> C2S3",
    "C2S3 -> {} + {}".format(ImportantSpecies.Oxaloglycolate.name, ImportantSpecies.Oxoaspartate.name),
    "{} <=> C2S4".format(ImportantSpecies.Oxaloglycolate.name),
    "C2S4 <=> C2S5",
    "C2S5 <=> C2S6",
    "{} -> C2S6".format(ImportantSpecies.Oxoaspartate.name),
    "{} + C2S6 -> C2S7".format(ImportantSpecies.Glyoxylate.name),
    "C2S7 -> C2S8",
    "C2S8 -> C2S9",
    "C2S9 -> C2S10"
]

extras = [
    '{} -> {}'.format(ImportantSpecies.Oxaloglycolate.name, ImportantSpecies.HCN.name)
]

cycle1_hyper = HyperGraph.from_abstract(*cycle1_reactions)
cycle2_hyper = HyperGraph.from_abstract(*cycle2_reactions)

cycle1_hyper.print()
cycle2_hyper.print()

reactions = cycle1_reactions + cycle2_reactions  #+ extras


def generate_rates(number_of_reactions, decomposed_rates=()):
    results = [0.0] * number_of_reactions
    decomposed_args = []

    for decompose_set in decomposed_rates:
        # decomposition of "chain reactions" into elementary reactions yields probability k / p where p
        # are the number reactions that the decomposition yields
        rand = random.random() / len(decompose_set)
        for arg in decompose_set:
            results[arg] = rand
            decomposed_args.append(arg)

    for i in range(number_of_reactions):
        if i not in decomposed_args:
            results[i] = random.random()
    return results


def print_params(params):
    print("Parameters are: {")
    for react, param in params.items():
        print("{!r}: {},".format(react, param))
    print("}")


def spectrum_plot(frequency, spectra, period_bounds):
    lower_bound, upper_bound = analytics.period_bounds(frequency, period_bounds[0], period_bounds[1])
    analytics.plot_spectra([spect[lower_bound: upper_bound] for spect in spectra],
        frequency[lower_bound: upper_bound])


def plot_minimal_rate_params(cycle1_min_rates, cycle2_min_rates, oscill_measurements):
    plt.figure()
    colormap = plt.cm.get_cmap('RdYlBu')
    plt.grid()

    vmax_value = max(oscill_measurements) + 10  # Let's scale the colorbar to match the maximum observed value
    scatter = plt.scatter(cycle1_min_rates, cycle2_min_rates, c=oscill_measurements, cmap=colormap, vmin=0,
                          vmax=vmax_value)

    plt.ylabel("cycle 2 minimal rate")
    plt.xlabel("cycle 1 minimal rate")
    plt.colorbar(scatter)


dg = HyperGraph.from_abstract(*reactions)
all_rates = generate_rates(len(reactions))

# parameters = {"Glyoxylate + C2S6 -> C2S7": 0.41593185562060364,
#               "C1S5 -> C1S6 + Glyoxylate": 0.03228617071642825,
#               "C2S2 -> C2S3": 0.7062744944670036,
#               "Oxaloglycolate <=> C2S4": 0.3567249083111612,
#               "C2S9 -> C2S10": 0.5568526471228114,
#               "C1S2 + Glyoxylate -> C1S3": 0.37969675068691977,
#               "C2S8 -> C2S9": 0.06244753992161167,
#               "2 HCN -> C1S1": 0.5920694109504293,
#               "C1S6 -> Glyoxylate": 0.6491898632004972,
#               "C2S4 <=> C2S5": 0.06373362319324183,
#               "C2S7 -> C2S8": 0.4887526649075856,
#               "C1S1 -> C1S2": 0.08334846163431975,
#               "C2S5 <=> C2S6": 0.263462182307307,
#               "Oxoaspartate -> C2S6": 0.4772774274488466,
#               "C1S4 -> C1S5": 0.030805076501288498,
#               "C2S10 + Glyoxylate -> C2S1": 0.49164100046643444,
#               "C2S1 -> C2S2": 0.007517466846686305,
#               "C2S3 -> Oxaloglycolate + Oxoaspartate": 0.7696745757637155,
#               "C1S3 -> C1S4": 0.17453627387117587}

initial_conditions = {
    ImportantSpecies.HCN.name: 2,
    ImportantSpecies.Glyoxylate.name: 2,
    ImportantSpecies.Oxaloglycolate.name: 1,
}

drain_params = {
    ImportantSpecies.HCN.name: {
        'in': {
            'constant': 0.1
        },
        'out': {
            'factor': 0.0001
        }
    },
    ImportantSpecies.Glyoxylate.name: {
        'in': {
            'constant': 0.002
        },
        'out': {
            'factor': 0.0001
        }
    },
    ImportantSpecies.Oxaloglycolate.name: {
        'out': {
            'factor': 0.002
        }
    }
}

parameter_matrix = tuple({r: random.random() for r in reactions} for _ in range(runs))

dg.print()

ode = dgDynamicSim(dg)
stochastic = dgDynamicSim(dg, 'stochastic')

for sym in ode.symbols:
    if sym not in drain_params:
        drain_params[sym] = {'out': {
            'factor': 0.0001
        }}

c1_minimal_values = []
c2_minimal_values = []
fourier_measurements = []
variance_measurements = []

for index, parm in enumerate(parameter_matrix):
    print("--- Run {} ---".format(index + 1))
    cycle1_params = [parm[k] for k in cycle1_reactions]
    cycle2_params = [parm[k] for k in cycle2_reactions]

    cycle1_minimal_rate = min(cycle1_params)
    cycle2_minimal_rate = min(cycle2_params)

    c1_minimal_values.append(cycle1_minimal_rate)
    c2_minimal_values.append(cycle2_minimal_rate)

    print("Cycle 1 reaction {!r} with minimal rate: {}"
          .format(cycle1_reactions[cycle1_params.index(cycle1_minimal_rate)], cycle1_minimal_rate))
    print("Cycle 2 reaction {!r} with minimal rate: {}"
          .format(cycle2_reactions[cycle2_params.index(cycle2_minimal_rate)], cycle2_minimal_rate))
    with stochastic('stochkit2') as stochkit2:
        sim_range = (60000, 3000)
        stochkit2.method = "tauLeaping"
        out = stochkit2(sim_range, initial_conditions, parm, drain_params)

        # Since we use numpy for our dependent and independent variables sets we can easily compute the variance
        variance_measurements.append(np.sum(out[0].dependent.var(axis=0)))
        print("sum variance measurement: {}".format(np.sum(out[0].dependent.var(axis=0))))

        analytics = DynamicAnalysisDevice(out[0])
        period_bounds = (600, sim_range[0] / 2)  # looking from 600 to 30000
        fourier_measurement = analytics.fourier_oscillation_measure(period_bounds[0], period_bounds[1])

        print("fourier oscillation measurement: {}".format(fourier_measurement))
        fourier_measurements.append(fourier_measurement)


plot_minimal_rate_params(c1_minimal_values, c2_minimal_values, fourier_measurements)


def fp(float_value, fixed_precision=18):
    """Fixed point string format conversion"""
    return "{:.{}f}".format(float_value, fixed_precision)

with open("eschenmoser_measurements_{}.tsv".format(runs), mode="w") as tsvfile:
    tsv_writer = csv.writer(tsvfile, delimiter="\t")
    tsv_writer.writerow(['param_n', 'variance_sum', 'fourier_score', 'lower_period_bound', 'upper_period_bound'] +
                        ['{!r}'.format(r) for r in reactions])
    for var_measure, fourier_measure, param_map in zip(variance_measurements, fourier_measurements, parameter_matrix):
        row = [len(reactions), fp(var_measure), fp(fourier_measure), fp(period_bounds[0]), fp(period_bounds[1])] + \
              [fp(param_map[r]) for r in reactions]
        tsv_writer.writerow(row)

show_plots()
