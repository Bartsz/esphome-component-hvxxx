MODEL_OPTIONS = [
    "HV160",
    "HV120",
    "HV110",
    "HV210",
]

# Allowed pressure ranges, taken from datasheet, in inH2O.
PRESSURE_RANGE_OPTIONS = [
    "0.1inh2o",
    "0.25inh2o",
    "0.5inh2o",
    "1inh2o",
    "2.5inh2o",
    "5inh2o",
    "10inh2o",
    "20inh2o",
    "30inh2o",
    "40inh2o",
    "50inh2o",
    "60inh2o",
]

PRESSURE_RANGE_TO_BITS = {
    "HV160": {
        "2.5inh2o": 0,
        "5inh2o": 1,
        "10inh2o": 2,
        "20inh2o": 3,
        "30inh2o": 4,
        "40inh2o": 5,
        "50inh2o": 6,
        "60inh2o": 7,
    },
    "HV120": {
        "2.5inh2o": 4,
        "5inh2o": 5,
        "10inh2o": 6,
        "20inh2o": 7,
    },
    "HV110": {
        "0.5inh2o": 2,
        "1inh2o": 3,
        "2.5inh2o": 4,
        "5inh2o": 5,
        "10inh2o": 6,
    },
    "HV210": {
        "0.1inh2o": 0,
        "0.25inh2o": 1,
        "0.5inh2o": 2,
        "1inh2o": 3,
        "2.5inh2o": 4,
        "5inh2o": 5,
        "10inh2o": 6,
    },
}

# Bits 4–7 of the Mode register
BANDWIDTH_MODES = {
    "0.1hz": 0,
    "0.25hz": 1,
    "0.5hz": 2,
    "1hz": 3,
    "2.5hz": 4,
    "5hz": 5,
    "10hz": 6,
    "auto": 7,
}
