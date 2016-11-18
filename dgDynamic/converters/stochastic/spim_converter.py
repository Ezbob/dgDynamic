import math
from io import StringIO
from ..convert_base import get_edge_rate_dict


def generate_preamble(sample_range, draw_automata=False, symbols_dict=None, species_count=0, ignored=None,
                      float_precision=18) -> str:

    with StringIO() as str_out:
        if isinstance(sample_range, (tuple, list, set)):
            if len(sample_range) >= 2:
                str_out.write("directive sample {:.{}f} {}\n".format(float(sample_range[0]), float_precision,
                                                                     sample_range[1]))
            elif len(sample_range) == 1:
                str_out.write("directive sample {:.{}f}\n".format(float(sample_range[0]), float_precision))
        elif issubclass(sample_range, float):
            str_out.write("directive sample {:.{}f}\n".format(sample_range, float_precision))

        if symbols_dict is not None:
            str_out.write("directive plot ")

            ignored_dict = dict(ignored)
            for index, symbol_mapping in enumerate(symbols_dict.items()):
                if ignored is not None:
                    if symbol_mapping[0] not in ignored_dict:
                        str_out.write("{}()".format(symbol_mapping[1]))
                        if index < (species_count - len(ignored)) - 1:
                            str_out.write("; ")
                else:
                    str_out.write("{}()".format(symbol_mapping[1]))
                    if index < species_count - 1:
                        str_out.write("; ")
            str_out.write("\n")

        if draw_automata:
            str_out.write("directive graph\n")

        return str_out.getvalue()


def generate_rates(channel_dict, parameters=None, float_precision=18) -> str:
    edge_rate_dict = get_edge_rate_dict(user_parameters=parameters)
    already_seen = dict()
    with StringIO() as str_out:
        for channel_tuple in channel_dict.values():
            for channel in channel_tuple:
                rate = edge_rate_dict[channel.channel_edge.id]
                if channel.rate_id not in already_seen:
                    if channel.is_decay:
                        str_out.write("val r{} = {:.{}f}\n".format(channel.rate_id, rate, float_precision))
                    else:
                        str_out.write("new chan{}@{:.{}f} : chan()\n".format(channel.rate_id, rate, float_precision))
                    already_seen[channel.rate_id] = True
        return str_out.getvalue()


def generate_initial_values(symbols_dict, initial_conditions) -> str:

    with StringIO() as str_out:
        str_out.write("run ( ")
        if isinstance(initial_conditions, dict):
            for index, key in enumerate(initial_conditions.keys()):
                if isinstance(initial_conditions[key], int):
                    str_out.write("{} of {}()".format(initial_conditions[key], symbols_dict[key]))

                    if index < len(initial_conditions) - 1:
                        str_out.write(" | ")
                else:
                    raise TypeError("Unsupported value type for key: {}".format(key))
        elif isinstance(initial_conditions, (tuple, list, set)):
            for index, rate_symbols in enumerate(zip(initial_conditions, symbols_dict.keys())):
                rate_value = rate_symbols[0]
                symbol_key = rate_symbols[1]
                if isinstance(rate_value, int):
                    str_out.write("{} of {}()".format(rate_value, symbols_dict[symbol_key]))

                    if index < len(initial_conditions) - 1:
                        str_out.write(" | ")
                else:
                    raise TypeError("Unsupported value type for element: {}".format(index))
        str_out.write(" )\n")
        return str_out.getvalue()


def generate_automata_code(channel_dict, symbols_dict, species_count):

    def generate_channel(stream, channel):

        def channel_solutions():
            if len(channel.solutions) > 1:
                stream.write("( ")
                for index_solution, solution in enumerate(channel.solutions):
                    stream.write("{}()".format(symbols_dict[solution]))
                    if index_solution < len(channel.solutions) - 1:
                        stream.write(' | ')
                stream.write(" )")
            elif len(channel.solutions) == 1:
                stream.write("{}()".format(symbols_dict[channel.solutions[0]]))
            else:
                stream.write("()")

        if channel.is_decay:
            stream.write('delay@r{}; '.format(channel.rate_id))
            channel_solutions()
        else:
            if channel.is_input:
                stream.write('?chan{}; '.format(channel.rate_id))
                channel_solutions()
            else:
                stream.write('!chan{}; '.format(channel.rate_id))
                channel_solutions()

    with StringIO() as str_result:
        str_result.write('let ')
        for symbol_index, symbol in enumerate(symbols_dict.items()):
            str_result.write("{}() = ".format(symbol[1]))

            if symbol[0] in channel_dict:
                current_channels = channel_dict[symbol[0]]
                if len(current_channels) == 1:
                    generate_channel(str_result, current_channels[0])
                elif len(current_channels) > 1:
                    str_result.write('do ')
                    for channel_index, channel in enumerate(current_channels):
                        generate_channel(str_result, channel)
                        if len(current_channels) - 1 > channel_index:
                            str_result.write(' or ')
            else:
                str_result.write('()')

            if symbol_index < species_count - 1:
                str_result.write('\nand ')
        return str_result.getvalue()
