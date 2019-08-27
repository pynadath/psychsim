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
actors_list = "actors_list"
criteria_list = "criteria_list"

DAY = "day"
ATTRIBUTE = "attribute"
ATTRIBUTE_VAL = "value"
OPERATOR = "operator"
OPERATOR_VALUES_IN = ["<", "<=", "=<", ">", ">=", "=>", "="]
ACTOR = "actor"
MODE_SELECTION = "mode_selection"
MODE_SELECTION_VALUES_IN = [random_str, ordered]
MODE_DISPLAY = "mode_display"
MODE_DISPLAY_VALUES_IN = [actors_list, criteria_list]
NUMBER = "number"
ENTITY = "entity"

QUERY_PARAM = {
    DAY: ["day", "d"],
    ACTOR: ["actor", "a"],
    ATTRIBUTE: ["attribute", "att"],
    MODE_SELECTION: ["mode_selection", "modeselect", "modeselection", "ms"],
    NUMBER: ["number", "n"],
    MODE_DISPLAY: ["mode_display", "mode display", "md"],
    ATTRIBUTE_VAL: ["value", "att_value", "val", "att_val"],
    OPERATOR: ["operator", "op", "o"],
    ENTITY: ["entity", "e"]
}
ALL_QUERY_PARAMS = [y for x in QUERY_PARAM.values() for y in x ]

# General info on simulation
COMMAND_GET_NDAYS = "get ndays", "get days", "get d"
COMMAND_GET_NACTORS = "get nactors", "get actors", "get a"
COMMAND_GET_ENTITIES = "get entities", "get e"
COMMAND_GET_ATTNAMES = "get attribute_names", "get attnames", "get att_n", "get att"

# Selecting agents
COMMAND_SELECT_NACTORS = "select actors", "select a", "s a", "select n", "s n"
COMMAND_RESET_SELECTION = "reset selection", "del actors", "del a", "reset s", "reset a", "r s"
COMMAND_SHOW_SELECTION = "show selection", "show s", "show a", "show actors"
COMMAND_APPLY_FILTER = "apply filter", "a f"

# Getting info about a specific agent
COMMAND_GET_VALUES = "get values", "get val", "get value", "get v"


CATEGORY_GENERAL_INFO = "--> General information about the simulation"
CATEGORY_SELECTING_ACTORS = "--> Selecting / deselecting actors"
CATEGORY_ACTOR_SPECIFIC = "--> Getting information about a specific actor"


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

        CATEGORY_SELECTING_ACTORS : {
             COMMAND_SELECT_NACTORS: {
                description: "Selects a group of actors to then execute queries on",
                parameters: [
                    {name: ACTOR,
                     optional: True},
                    {name: MODE_SELECTION,
                     optional: True},
                    {name: NUMBER,
                     optional: False}
                ]
            },
            COMMAND_RESET_SELECTION: {
                description: "Resets the selection / forgets selection criteria (selects all actors)",
                parameters: ""
            },
            COMMAND_SHOW_SELECTION: {
                description: "Show the actors (mode actors_list) selected or the criteria (more criteria_list) used to selec the actors",
                parameters: [
                    {name: MODE_DISPLAY,
                     optional: False}
                ]
            },
            COMMAND_APPLY_FILTER: {
                description: "Applies a filter a selection",
                parameters : [
                    {name: ATTRIBUTE,
                     optional: False},
                    {name: OPERATOR,
                     optional: False},
                    {name: ATTRIBUTE_VAL,
                     optional: False},
                    {name: DAY,
                     optional: False}
                ]
            }
        },

        CATEGORY_ACTOR_SPECIFIC: {
            COMMAND_GET_VALUES: {
                description: "Returns the beliefs of the agent at a specific day",
                parameters: [
                    {name: DAY,
                     optional: False},
                    {name: ACTOR,
                     optional: False},
                    {name: ATTRIBUTE,
                     optional: True}
                ]
            }
        }
    },
    parameters: {
        DAY: {
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
        MODE_DISPLAY: {
            value_type: "str",
            description: "Mode for displaying selection",
            values_in: MODE_DISPLAY_VALUES_IN
        },
        NUMBER: {
            value_type: "int",
            description: "Integer"
        },
        ENTITY: {
            value_type: "Name of an entity (str)",
            description: "E.g. in GROUND TRUTH, Actor or Region"
        }
    }
}
