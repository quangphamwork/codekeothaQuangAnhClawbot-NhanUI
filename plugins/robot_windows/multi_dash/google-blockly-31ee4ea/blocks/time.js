'use strict';

var timeColor = 80;

Blockly.defineBlocksWithJsonArray([
  {
    "type": "time_delay",
    "message0": "delay %1 s",
    "args0": [
      {
        "type": "input_value",
        "name": "ms",
        "check": "Number"
      }
    ],
    "previousStatement": null,
    "nextStatement": null,
    "colour": timeColor,
    "tooltip": "DESCRIPTION: Suspends the program for a specified number of seconds\nPARAMETERS: Number of seconds\nRETURN: None",
    "helpUrl": ""
  },
  {
    "type": "time_gettime",
    "message0": "getTime",
    "output": null,
    "colour": timeColor,
    "tooltip": "DESCRIPTION: Returns elapsed simulation time in seconds\nPARAMETERS: None\nRETURN: Time in seconds",
    "helpUrl": ""
  },
  {
    "type": "time_resettime",
    "message0": "resetTime",
    "previousStatement": null,
    "nextStatement": null,
    "colour": timeColor,
    "tooltip": "DESCRIPTION: Reserved for compatibility\nPARAMETERS: None\nRETURN: None",
    "helpUrl": ""
  }
]);
