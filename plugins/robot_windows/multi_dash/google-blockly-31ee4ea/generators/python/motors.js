Blockly.Python['motors_go_forward'] = function(block) {
  var value_speed = Blockly.Python.valueToCode(block, 'speed', Blockly.Python.ORDER_ATOMIC) || '0';
  return 'robot.go_forward(' + value_speed + ')\n';
};

Blockly.Python['motors_go_backward'] = function(block) {
  var value_speed = Blockly.Python.valueToCode(block, 'speed', Blockly.Python.ORDER_ATOMIC) || '0';
  return 'robot.go_backward(' + value_speed + ')\n';
};

Blockly.Python['motors_turn_left'] = function(block) {
  var value_speed = Blockly.Python.valueToCode(block, 'speed', Blockly.Python.ORDER_ATOMIC) || '0';
  return 'robot.turn_left(' + value_speed + ')\n';
};

Blockly.Python['motors_turn_right'] = function(block) {
  var value_speed = Blockly.Python.valueToCode(block, 'speed', Blockly.Python.ORDER_ATOMIC) || '0';
  return 'robot.turn_right(' + value_speed + ')\n';
};

// Legacy blocks kept for backward compatibility with old saved projects.
Blockly.Python['motors_setupmotor'] = function(block) {
  var variable_motorObj = Blockly.Python.variableDB_.getName(block.getFieldValue('motorObj'), Blockly.Variables.NAME_TYPE);
  var text_motorName = block.getFieldValue('motorName') || '';
  return '__legacy_bind_motor("' + variable_motorObj + '", "' + text_motorName.replace(/"/g, '\\"') + '")\n';
};

Blockly.Python['motors_setspeed'] = function(block) {
  var variable_motorObj = Blockly.Python.variableDB_.getName(block.getFieldValue('motorObj'), Blockly.Variables.NAME_TYPE);
  var value_motorSpeed = Blockly.Python.valueToCode(block, 'motorSpeed', Blockly.Python.ORDER_ATOMIC) || '0';
  return '__legacy_set_motor_speed("' + variable_motorObj + '", ' + value_motorSpeed + ')\n';
};

Blockly.Python['motors_resetencoders'] = function(block) {
  var variable_motorObj = Blockly.Python.variableDB_.getName(block.getFieldValue('motorObj'), Blockly.Variables.NAME_TYPE);
  var code = 'getEncoders(encObj[' + variable_motorObj + '])\n' +
             'lastEncReset[encObj[' + variable_motorObj + ']] = encCount[encObj[' + variable_motorObj + ']]\n';
  return code;
};

Blockly.Python['motors_getencoders'] = function(block) {
  var variable_motorObj = Blockly.Python.variableDB_.getName(block.getFieldValue('motorObj'), Blockly.Variables.NAME_TYPE);
  var code = 'getEncoders(encObj[' + variable_motorObj + ']) or encCount[encObj[' + variable_motorObj + ']] - lastEncReset[encObj[' + variable_motorObj + ']]';
  return [code, Blockly.Python.ORDER_NONE];
};
