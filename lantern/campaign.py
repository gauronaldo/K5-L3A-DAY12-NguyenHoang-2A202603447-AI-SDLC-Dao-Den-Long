"""Three-night sequence (Ticket-02 Part 3): menu -> intro -> play -> result -> next night / retry / dawn."""
from . import config as C

ONG_DANG = {
    1: "Ông Đăng: \"Sương đen nuốt mất Đảo Bến rồi, cháu ạ. Gom đom đóm, thắp lại năm ngọn Đèn Lồng Lớn. "
       "Bóng Mực sợ ánh đèn — đứng gần đèn đã sáng là an toàn.\"",
    2: "Ông Đăng: \"Đảo Cau có hai hòn nối bằng cầu tre, không lan can đâu. Bục nhảy sẽ đưa cháu qua đảo kia. "
       "Coi chừng Gió Lạc — nó chỉ thích cướp đom đóm thôi.\"",
    3: "Ông Đăng: \"Đảo Chuông cao ba tầng, gió mạnh thổi từng cơn. Lên dốc, nhảy bục để tới tháp chuông. "
       "Thắp đủ bảy ngọn đèn thì trời sẽ sáng.\"",
}


class Campaign:
    def __init__(self):
        self.reset()

    def reset(self):
        self.night = 1
        self.total = 0          # sum of scores of nights won
        self.nights_won = 0
        self.history = []       # (night, result, score)
        self.finished = False   # dawn reached (won night 3)

    def intro(self):
        return C.NIGHTS[self.night]["name"], ONG_DANG[self.night]

    def night_over(self, result, score):
        """Record a finished night. Returns 'next', 'retry' or 'dawn'."""
        self.history.append((self.night, result, score))
        if result != "won":
            return "retry"
        self.total += score
        self.nights_won += 1
        if self.night == 3:
            self.finished = True
            return "dawn"
        return "next"

    def advance(self):
        if self.night < 3:
            self.night += 1
