description = "description"
parameters = "param"
commands = "commands"
value_type = "type"
name = "name"
optional = "optional"

DAY = "day"
ATTRIBUTE = "attribute"
ACTOR = "actor"

QUERY_PARAM = {
    DAY: ["day", "d"],
    ACTOR: ["actor", "a"],
    ATTRIBUTE: ["attribute", "att"]
}
ALL_QUERY_PARAMS = [y for x in QUERY_PARAM.values() for y in x ]


COMMAND_GET_ATTRIBUTES = "get attributes", "get att", "get attribute"
COMMAND_GET_NDAYS = "get ndays", "get days"
COMMAND_GET_NACTORS = "get nactors", "get actors", "get a"


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
        }
    }

}
