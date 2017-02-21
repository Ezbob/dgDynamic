from dgDynamic import dgDynamicSim, HyperGraph, show_plots
from dgDynamic.choices import ScipyOdeSolvers
from dgDynamic.analytics import DynamicAnalysisDevice
import random
import enum


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

for i in range(1):
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

    parameter_matrix = tuple({r: random.random() for r in reactions} for _ in range(1))

    #print("Parameters are: {")
    #for react, param in parameters.items():
    #    print("{!r}: {},".format(react, param))
    #print("}")

    dg.print()

    ode = dgDynamicSim(dg)
    stochastic = dgDynamicSim(dg, 'stochastic')

    for sym in ode.symbols:
        if sym not in drain_params:
            drain_params[sym] = {'out': {
                'factor': 0.0001
            }}

    for parm in parameter_matrix:
        #with ode('scipy') as scipy:
        #    int_range = (0, 60000)
        #    scipy.integrator_mode = ScipyOdeSolvers.LSODA
        #    scipy(int_range, initial_conditions, parm, drain_params).plot(figure_size=(40, 20))

        with stochastic('stochkit2') as stochkit2:
            sim_range = (60000, 3000)
            stochkit2.method = "tauLeaping"
            out = stochkit2(sim_range, initial_conditions, parm, drain_params).plot(figure_size=(40, 20))

            out.save("emoser")

            anna = DynamicAnalysisDevice(out[0])
            freqs = anna.fourier_frequencies
            anna.plot_spectra(anna.power_spectra, freqs, include_maxima=True, include_maximum=True, is_power_spectra=True)
            for symbol, spectrum in zip(stochastic.symbols, anna.power_spectra):
                maximum, maximum_freq = anna.nonzero_maximum(spectrum, freqs)
                print(symbol, maximum, maximum_freq)

show_plots()
