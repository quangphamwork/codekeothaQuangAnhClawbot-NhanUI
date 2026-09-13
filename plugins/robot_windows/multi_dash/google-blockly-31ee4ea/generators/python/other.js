Blockly.Python['other_start'] = function(block) {
  // 1. Chỉ import thư viện toán
  var code = 'import math\n';
  
  // 2. KHÔNG TẠO ROBOT MỚI!
  // Map biến 'myRobot' vào biến 'robot' toàn cục đã có sẵn trong 123.py
  code += 'myRobot = robot\n'; 
  code += 'timeStep = int(robot.getBasicTimeStep())\n'; 
  
  // 3. CÁC HÀM HELPER (Giữ nguyên logic cũ)
  code += 'kernel_size = 10\n' + 
          'internal_angle = 0.0\n' +
          'encObj = {}\n' +
          'lastTimeReset = 0\n' +
          'gyroEnable = False\n' +
          'encCount = {}\n' +
          'lastEncReset = {}\n\n';

  code += 'def getLSColor(camImg):\n' +
            ' global kernel_size\n' +
            ' rgb = [0] * 3\n' +
            ' for x in range(0,kernel_size):\n' +
            '  for y in range(0,kernel_size):\n' +
            '   for i in range(0,3):\n' +
            '    rgb[i] += camImg[x][y][i]\n' +
            ' for i in range(0,3):\n' +
            '  rgb[i] = int(rgb[i]/(kernel_size*kernel_size))\n' +
            ' return rgb\n' +
            'def getLSGray(camImg):\n' +
            ' global kernel_size\n' +
            ' gray = 0\n' +
            ' for x in range(0,kernel_size):\n' +
            '  for y in range(0,kernel_size):\n' +
            '   for i in range(0,3):\n' +
            '    gray += camImg[x][y][i]\n' +
            ' gray = int(gray/(3*kernel_size*kernel_size))\n' +
            ' return gray\n\n';
            
  code += 'def updateGyro():\n' +
          ' global internal_angle\n' +
          ' internal_angle += (timeStep / 1000.0) * (gyro.getValues())[1]\n\n' +
          'def getAngle():\n' +
          ' global internal_angle\n' +
          ' return internal_angle * 180.0 / 3.1415\n\n';

  code += 'def getEncoders(posSensor):\n' +
          '  global encCount\n' +
          '  encCount[posSensor] = posSensor.getValue() / 3.1415 * 180.0\n' +
          '  if encCount[posSensor] != encCount[posSensor]:\n' +
          '    encCount[posSensor] = 0\n' +
          '  return False\n\n' +
          'def getObjAng(coord):\n' +
          '    ang = math.degrees(math.atan(coord[0]/math.fabs(coord[2])))\n' +
          '    return ang\n\n';

  // 4. QUAN TRỌNG: KHÔNG SINH RA VÒNG LẶP WHILE Ở ĐÂY NỮA
  // Code sẽ chạy thẳng tuột từ trên xuống dưới rồi trả quyền lại cho Controller
  return code;
};

Blockly.Python['other_end'] = function(block) {
  return '';
};