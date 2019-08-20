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
ACTOR = "actor"
MODE_SELECTION = "mode_selection"
MODE_SELECTION_VALUES_IN = [random_str, ordered]
MODE_DISPLAY = "mode_display"
MODE_DISPLAY_VALUES_IN = [actors_list, criteria_list]
NUMBER = "number"

QUERY_PARAM = {
    DAY: ["day", "d"],
    ACTOR: ["actor", "a"],
    ATTRIBUTE: ["attribute", "att"],
    MODE_SELECTION: ["mode_selection", "modeselect", "modeselection", "ms"],
    NUMBER: ["number", "n"],
    MODE_DISPLAY: ["mode_display", "mode display", "md"]
}
ALL_QUERY_PARAMS = [y for x in QUERY_PARAM.values() for y in x ]


COMMAND_GET_ATTRIBUTES = "get attributes", "get att", "get attribute"
COMMAND_GET_NDAYS = "get ndays", "get days"
COMMAND_GET_NACTORS = "get nactors", "get actors", "get a"
COMMAND_SELECT_ACTORS = "select actors", "select a", "s a"
COMMAND_DESELECT_ACTORS = "deselect actors", "del actors", "del a"
COMMAND_SHOW_SELECTION = "show selection", "show s", "show a", "show actors"


HELP = {
    commands: {
        COMMAND_GET_ATTRIBUTES: {
            description: "Returns a list of attributes",
            parameters: [
                {name: DAY,
                 optional: True},
                {name: ATTRIBUTE,
                 optional: True},
                {name: ACTOR,
                 optional: False}
            ]
        },
        COMMAND_SELECT_ACTORS: {
            description: "Selects a group of actors to then execute queries on",
            parameters: [
                {name: DAY,
                 optional: True},
                {name: ATTRIBUTE,
                 optional: True},
                {name: ACTOR,
                 optional: True},
                {name: MODE_SELECTION,
                 optional: True},
                {name: NUMBER,
                 optional: False}
            ]
        },
        COMMAND_DESELECT_ACTORS: {
            description: "Deselects the actors",
            parameters: ""
        },
        COMMAND_SHOW_SELECTION: {
            description: "Show the actors (mode actors_list) selected or the criteria (more criteria_list) used to selec the actors",
            parameters: [
                {name: MODE_DISPLAY,
                 optional: False}
            ]
        },
        COMMAND_GET_NDAYS: {
            description: "Returns the number of days in the simulation",
            parameters: []
        },
        COMMAND_GET_NACTORS: {
            description: "Returns the number of actors in the simulation",
            parameters: []
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
        }
    }
}
