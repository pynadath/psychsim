THISISFALSE = "thisisfalse"

description = "description"
parameters = "param"
commands = "commands"
value_type = "type"
name = "name"
optional = "optional"
values_in = "values in"
empty = "empty"
random_str = "random"
ordered = "ordered"
# actors_list = "actors_list"
# filters_list = "filters_list"
active = "active"
active_values = ["active", "on"]
inactive_values = ["inactive", "off"]
all_values = ["all"]

DAYS = "day"
ATTRIBUTE = "attribute"
ATTRIBUTE_VAL = "value"
OPERATOR = "operator"
OPERATOR_VALUES_IN = ["<", "<=", "=<", ">", ">=", "=>", "="]
ACTOR = "actor"
MODE_SELECTION = "mode_selection"
MODE_SELECTION_VALUES_IN = [random_str, ordered]
NUMBER = "number"
ENTITY = "entity"
NAME = "name"
TYPE = "type"
TYPE_VALUES_IN = active_values + inactive_values + all_values
ACTORS_LIST = "actors_list"
STAT_FCTS = "stat_functions"
STAT_FCT_VALUES_IN = ["mean", "median", "variation", "std_dev", "list"]

QUERY_PARAM = {
    DAYS: ["days", "day", "d"],
    ACTOR: ["actor", "a"],
    ATTRIBUTE: ["attribute", "att"],
    MODE_SELECTION: ["mode_selection", "modeselect", "modeselection", "ms"],
    NUMBER: ["number", "n"],
    ATTRIBUTE_VAL: ["value", "att_value", "val", "att_val"],
    OPERATOR: ["operator", "op", "o"],
    ENTITY: ["entity", "e"],
    NAME: ["name", "n"],
    TYPE: ["type", "t"],
    ACTORS_LIST: [ACTORS_LIST, "a_list"],
    STAT_FCTS: [STAT_FCTS, "stat_fct", "function", "fct"]
}
ALL_QUERY_PARAMS = [y for x in QUERY_PARAM.values() for y in x ]

# General info on simulation
CATEGORY_GENERAL_INFO = "--> General information about the simulation"
COMMAND_GET_NDAYS = "get ndays", "get days", "get d"
COMMAND_GET_NACTORS = "get nactors", "get actors", "get a"
COMMAND_GET_ENTITIES = "get entities", "get e"
COMMAND_GET_ATTNAMES = "get attribute_names", "get attnames", "get att_n", "get att"

# Selecting agents
CATEGORY_SELECTING_ACTORS = "--> Selecting / deselecting actors"
COMMAND_SELECT_NACTORS = "select n_actors", "select a", "s a", "select n", "s n"
COMMAND_SELECT_ACTORS_BY_NAME = "select actors_by_name", "selection actors_by_name"
COMMAND_RESET_SELECTION = "reset selection", "del actors", "del a", "reset s", "reset a", "r s"
COMMAND_SHOW_SELECTION = "show selection", "show s", "show a", "show actors", "display selection", "display s", "display a", "display actors"
COMMAND_SHOW_FILTERS = "show filters", "show f", "s f", "display filters", "display f", "d f"
COMMAND_APPLY_FILTER = "apply filter", "a f"
COMMAND_DEACTIVATE_FILTER = "deactivate filter", "cancel filter", "c f"
COMMAND_REACTIVATE_FILTER = "reactivate filter", "r f"

# Getting info about a specific agent
CATEGORY_ACTOR_SPECIFIC = "--> Getting information about a specific actor"
COMMAND_GET_VALUES = "get values", "get val", "get value", "get v"

# Getting stats
CATEGORY_STATS_FUNCTIONS = "--> Counting / doing stats over agent selection"
COMMAND_COUNT_ACTORS = "count actors", "count"
COMMAND_GET_STATS = "get stats", "get statistics"


HELP = {
    commands: {
        CATEGORY_GENERAL_INFO: {
            COMMAND_GET_NDAYS: {
                description: "Returns the number of days in the simulation",
                parameters: []
            },
            COMMAND_GET_NACTORS: {
                description: "Returns the number of actors in the simulation",
                parameters: []
            },
            COMMAND_GET_ENTITIES: {
                description: "Returns categories of entities present in the simulation (e.g. Actor)",
                parameters: []
            },
            COMMAND_GET_ATTNAMES: {
                description: "Returns the list of attributes attached to an entity",
                parameters: [
                    {name: ENTITY,
                     optional: False}
                ]
            }
        },

        CATEGORY_SELECTING_ACTORS: {
            COMMAND_SELECT_NACTORS: {
                description: "Selects a group of actors to then execute queries on",
                parameters: [
                    {name: MODE_SELECTION,
                     optional: True},
                    {name: NUMBER,
                     optional: False}
                ]
            },
            COMMAND_SELECT_ACTORS_BY_NAME: {
                description: "Selects the actors listed by the user",
                parameters: [
                    {name: ACTORS_LIST,
                     optional: False}
                ]
            },
            COMMAND_RESET_SELECTION: {
                description: "Resets the selection / forgets selection criteria (selects all actors)",
                parameters: []
            },
            COMMAND_SHOW_SELECTION: {
                description: "Show the actors selected (list of names)",
                parameters: []
            },
            COMMAND_SHOW_FILTERS: {
                description: "Shows the filters used for actor selection",
                parameters: [
                    {name: TYPE,
                     optional: False}
                ]
            },
            COMMAND_APPLY_FILTER: {
                description: "Applies a filter a selection",
                parameters: [
                    {name: ATTRIBUTE,
                     optional: False},
                    {name: OPERATOR,
                     optional: False},
                    {name: ATTRIBUTE_VAL,
                     optional: False},
                    {name: DAYS,
                     optional: False},
                    {name: NAME,
                     optional: True}
                ]
            },
            COMMAND_DEACTIVATE_FILTER: {
                description: "Inactivates the filter",
                parameters: [
                    {name: NAME,
                     optional: False}
                ]
            },
            COMMAND_REACTIVATE_FILTER: {
                description: "Reactivates the filter",
                parameters: [
                    {name: NAME,
                     optional: False}
                ]
            }
        },

        CATEGORY_ACTOR_SPECIFIC: {
            COMMAND_GET_VALUES: {
                description: "Returns the beliefs of the agent at a specific day",
                parameters: [
                    {name: DAYS,
                     optional: False},
                    {name: ACTOR,
                     optional: False},
                    {name: ATTRIBUTE,
                     optional: True}
                ]
            }
        },
        
        CATEGORY_STATS_FUNCTIONS: {
            COMMAND_COUNT_ACTORS: {
                description: "Counts the actors, amoug those selected, that fulfil a specific criteria",
                parameters: [
                    {name: DAYS,
                     optional: True},
                    {name: ATTRIBUTE,
                     optional: False},
                    {name: OPERATOR,
                     optional: False},
                    {name:ATTRIBUTE_VAL,
                     optional: False},
                    {name: NAME,
                     optional: True}
                ]
            },
            COMMAND_GET_STATS: {
                description: "Computes statistics over attribute passed as a parameter and the selected actors.",
                parameters: [
                    {name: DAYS,
                     optional: True},
                    {name: ATTRIBUTE,
                     optional: False},
                    {name: NAME,
                     optional: True},
                    {name: STAT_FCTS,
                     optional: True,
                     values_in: STAT_FCT_VALUES_IN}
                ]
            }
        }
    },
    parameters: {
        DAYS: {
            value_type: "int",
            description: "Focus on given day"
        },
        ATTRIBUTE: {
            value_type: "str",
            description: "Focus on given attribute. (An attribute is for exmaple \"health\" for an Actor.)"
        },
        ATTRIBUTE_VAL: {
            value_type: "undefined (depends on the attribute)",
            description: "Used with the %s parameter: gives a value to the attribute (e.g. to filter a selection)" %ATTRIBUTE
        },
        OPERATOR: {
            value_type: "str / mathematical operator",
            description: "Used with the %s and %s parameter: operator to apply. (e.g. to filter a selection)" % (ATTRIBUTE, ATTRIBUTE_VAL),
            values_in: OPERATOR_VALUES_IN
        },
        ACTOR: {
            value_type: "int",
            description: "Focus on actor #x"
        },
        MODE_SELECTION: {
            value_type: "str",
            description: "Mode for selecting agents",
            values_in: MODE_SELECTION_VALUES_IN
        },
        NUMBER: {
            value_type: "int",
            description: "Integer"
        },
        ENTITY: {
            value_type: "Name of an entity (str)",
            description: "E.g. in GROUND TRUTH, Actor or Region"
        },
        NAME: {
            value_type: "str",
            description: "Allows the user to set a name (e.g. for filters)"
        },
        TYPE: {
            value_type: "string",
            description: "Type of filter you want to display (active / inactive / all)"
        }
    }
}

ALL_COMMANDS = {}
for command_categories in HELP[commands].values():
    for c_name, c_obj in command_categories.items():
        ALL_COMMANDS[c_name] = c_obj
