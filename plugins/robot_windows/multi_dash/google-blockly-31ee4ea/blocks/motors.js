'use strict';

var motorColor = 120;

Blockly.defineBlocksWithJsonArray([
  {
    "type": "motors_go_forward",
    "message0": "goForward %1 %%",
    "args0": [
      {
        "type": "input_value",
        "name": "speed",
        "check": "Number"
      }
    ],
    "previousStatement": null,
    "nextStatement": null,
    "colour": motorColor,
    "tooltip": "DESCRIPTION: Move robot forward\nPARAMETERS: speed 0..100 (%)\nRETURN: None",
    "helpUrl": ""
  },
  {
    "type": "motors_go_backward",
    "message0": "goBackward %1 %%",
    "args0": [
      {
        "type": "input_value",
        "name": "speed",
        "check": "Number"
      }
    ],
    "previousStatement": null,
    "nextStatement": null,
    "colour": motorColor,
    "tooltip": "DESCRIPTION: Move robot backward\nPARAMETERS: speed 0..100 (%)\nRETURN: None",
    "helpUrl": ""
  },
  {
    "type": "motors_turn_left",
    "message0": "turnLeft %1 %%",
    "args0": [
      {
        "type": "input_value",
        "name": "speed",
        "check": "Number"
      }
    ],
    "previousStatement": null,
    "nextStatement": null,
    "colour": motorColor,
    "tooltip": "DESCRIPTION: Turn robot left in place\nPARAMETERS: speed 0..100 (%)\nRETURN: None",
    "helpUrl": ""
  },
  {
    "type": "motors_turn_right",
    "message0": "turnRight %1 %%",
    "args0": [
      {
        "type": "input_value",
        "name": "speed",
        "check": "Number"
      }
    ],
    "previousStatement": null,
    "nextStatement": null,
    "colour": motorColor,
    "tooltip": "DESCRIPTION: Turn robot right in place\nPARAMETERS: speed 0..100 (%)\nRETURN: None",
    "helpUrl": ""
  },

  {
    "type": "motors_setupmotor",
    "message0": "setupMotor %1 %2",
    "args0": [
      {
        "type": "field_variable",
        "name": "motorObj",
        "variable": "motorObj"
      },
      {
        "type": "field_input",
        "name": "motorName",
        "text": "motorName"
      }
    ],
    "previousStatement": null,
    "nextStatement": null,
    "colour": motorColor,
    "tooltip": "LEGACY: keeps backward compatibility for old projects",
    "helpUrl": ""
  },
  {
    "type": "motors_setspeed",
    "message0": "setSpeed %1 %2 %%",
    "args0": [
      {
        "type": "field_variable",
        "name": "motorObj",
        "variable": "motorObj"
      },
      {
        "type": "input_value",
        "name": "motorSpeed"
      }
    ],
    "previousStatement": null,
    "nextStatement": null,
    "colour": motorColor,
    "tooltip": "LEGACY: keeps backward compatibility for old projects",
    "helpUrl": ""
  }
]);
