'use strict';

var gripperColor = 290; // Màu tím cho gripper

Blockly.defineBlocksWithJsonArray([
  // ===== BLOCK GẮP VẬT =====
  {
    "type": "gripper_grip",
    "message0": "🦾 grip %1 °",
    "args0": [
      {
        "type": "input_value",
        "name": "angle",
        "check": "Number"
      }
    ],
    "previousStatement": null,
    "nextStatement": null,
    "colour": gripperColor,
    "tooltip": "DESCRIPTION: Close gripper to grab object\nPARAMETERS: angle in degrees (default 30)\nRETURN: None",
    "helpUrl": ""
  },
  
  // ===== BLOCK THẢ VẬT =====
  {
    "type": "gripper_release",
    "message0": "✋ release %1 °",
    "args0": [
      {
        "type": "input_value",
        "name": "angle",
        "check": "Number"
      }
    ],
    "previousStatement": null,
    "nextStatement": null,
    "colour": gripperColor,
    "tooltip": "DESCRIPTION: Open gripper to release object\nPARAMETERS: angle in degrees (default -10)\nRETURN: None",
    "helpUrl": ""
  },

  // ===== BLOCK NÂNG TAY =====
  {
    "type": "arm_up",
    "message0": "⬆️ arm up %1 °",
    "args0": [
      {
        "type": "input_value",
        "name": "angle",
        "check": "Number"
      }
    ],
    "previousStatement": null,
    "nextStatement": null,
    "colour": gripperColor,
    "tooltip": "DESCRIPTION: Raise arm up\nPARAMETERS: angle in degrees (default 0 = horizontal)\nRETURN: None",
    "helpUrl": ""
  },

  // ===== BLOCK HẠ TAY =====
  {
    "type": "arm_down",
    "message0": "⬇️ arm down %1 °",
    "args0": [
      {
        "type": "input_value",
        "name": "angle",
        "check": "Number"
      }
    ],
    "previousStatement": null,
    "nextStatement": null,
    "colour": gripperColor,
    "tooltip": "DESCRIPTION: Lower arm down\nPARAMETERS: angle in degrees (default 45)\nRETURN: None",
    "helpUrl": ""
  }
]);
