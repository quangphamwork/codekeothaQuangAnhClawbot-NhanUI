from library import SumoRobot

if __name__ == "__main__":
    robot = SumoRobot()

    def delay(duration_s: float) -> None:
        robot.delay(duration_s)

    while True:
# ====== LẬP TRÌNH TỪ ĐÂY TRỞ XUỐNG CÁC BẠN NHÉ======
        robot.go_forward(30)
        delay(6)
        # BƯỚC 1: quay phải vận tốc 15% trong 5 giây
        robot.turn_right(30)
        delay(5)

        # BƯỚC 2: quay trái vận tốc 15% trong 5 giây
        robot.turn_left(30)
        delay(5)

        # BƯỚC 3: di chuyển thẳng vận tốc 15% trong 6 giây
        robot.go_forward(30)
        delay(6)

        # BƯỚC 4: di chuyển lùi vận tốc 40% trong 6 giây
        # robot.go_backward(40)
        # delay(6)
        

        
