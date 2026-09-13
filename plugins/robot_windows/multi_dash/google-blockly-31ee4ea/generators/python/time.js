Blockly.Python['time_delay'] = function(block) {
  var value_seconds = Blockly.Python.valueToCode(block, 'ms', Blockly.Python.ORDER_ATOMIC) || '0';
  return 'delay(' + value_seconds + ')\n';
};

Blockly.Python['time_gettime'] = function(block) {
  var code = 'robot.getTime()';
  return [code, Blockly.Python.ORDER_ATOMIC];
};

Blockly.Python['time_resettime'] = function(block) {
  var code = 'pass # Reset time requires supervisor logic\n';
  return code;
};
