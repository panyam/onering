
import os

def parse_line_dict(line):
    """
    Parses a given line that is a list of key/value pairs seperated by spaces or commas.
    eg:

        a=b c = "d" e = "f  ", g = k = 4

    Returns a dictionary where the key is the string and value is a list of values for the key.
    """
    line = line.strip()
    out = {}
    curr_key = ""
    curr_value = ""
    entry_index = 0
    chindex = 0
    return out

def split_list_at(predicate, input_list):
    """
    Splits a given input list at the index where the predicate matches for the first time.

    Returns     P1, (index, predicate_value), P2 where
    P1              -   All items before the predicate matched
    index           -   Index of the item that matched the predicate.
    predicate_value -   input_list[index]
    P2              -   All items after the predicate matched
    """

    p1 = []
    p2 = []
    found = True
    index = -1
    for i,element in enumerate(input_list):
        if predicate(input_list):
            index = i
            break
    if index < 0:
        return input_list, (-1, None), []
    else:
        return input_list[:index], (index, input[index]), input_list[index + 1:]

def collect_files(root_dir):
    for root, dirs, files in os.walk(root_dir, topdown=False):
        for name in files:
            full_path = os.path.join(root, name)
            yield full_path

def collect_files_by_extension(root_dir, ext):
    return filter(lambda path: path.endswith("." + ext) and os.path.isfile(path), collect_files(root_dir))

def collect_jars(root_dir):
    def is_model_jar(name):
        return name.find("data-template") > 0 and name.find("SNAPSHOT") < 0 and name.endswith(".jar")
    return filter(is_model_jar, collect_files(root_dir))

from optparse import Option
class ListOption(Option):
    ACTIONS = Option.ACTIONS + ("extend",)
    STORE_ACTIONS = Option.STORE_ACTIONS + ("extend",)
    TYPED_ACTIONS = Option.TYPED_ACTIONS + ("extend",)
    ALWAYS_TYPED_ACTIONS = Option.ALWAYS_TYPED_ACTIONS + ("extend",)

    def take_action(self, action, dest, opt, value, values, parser):
        if action == "extend":
            lvalue = value.split(",")
            values.ensure_value(dest, []).extend(lvalue)
        else:
            Option.take_action(self, action, dest, opt, value, values, parser)
