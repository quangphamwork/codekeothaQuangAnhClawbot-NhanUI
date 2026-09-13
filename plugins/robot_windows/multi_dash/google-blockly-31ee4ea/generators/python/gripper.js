// Python code generators for Gripper blocks

Blockly.Python['gripper_grip'] = function(block) {
  var value_angle = Blockly.Python.valueToCode(block, 'angle', Blockly.Python.ORDER_ATOMIC) || '30';
  return 'robot.close_gripper(' + value_angle + ')\n';
};

Blockly.Python['gripper_release'] = function(block) {
  var value_angle = Blockly.Python.valueToCode(block, 'angle', Blockly.Python.ORDER_ATOMIC) || '-10';
  return 'robot.open_gripper(' + value_angle + ')\n';
};

Blockly.Python['arm_up'] = function(block) {
  var value_angle = Blockly.Python.valueToCode(block, 'angle', Blockly.Python.ORDER_ATOMIC) || '0';
  return 'robot.arm_up(' + value_angle + ')\n';
};

Blockly.Python['arm_down'] = function(block) {
  var value_angle = Blockly.Python.valueToCode(block, 'angle', Blockly.Python.ORDER_ATOMIC) || '45';
  return 'robot.arm_down(' + value_angle + ')\n';
};
