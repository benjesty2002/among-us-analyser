import cv2

from SceneExtractor import SceneExtractor
from VoteScreenAnalyser import VoteScreen
import os


def run_all():
    root_dir = r"F:\Videos\Among Us"
    for item in os.listdir(root_dir):
        if os.path.isdir(os.path.join(root_dir, item)):
            print("Checking path {}".format(os.path.join(root_dir, item)))
            date_str = item
            filepath_no_number = os.path.join(root_dir, date_str, "Among_Us_{}.mp4".format(date_str))
            round_num = 1
            filepath_numbered = os.path.join(root_dir, date_str, "Among_Us_{} ({}).mp4".format(date_str, round_num))
            if os.path.exists(filepath_no_number) and not os.path.exists(filepath_numbered):
                os.rename(filepath_no_number, filepath_numbered)
            while os.path.exists(filepath_numbered):
                print("Processing round {}".format(round_num))
                print("filepath: {}".format(filepath_numbered))
                se = SceneExtractor(round_num=round_num, date_str=date_str)
                se.export_round_details()
                round_num += 1
                filepath_numbered = os.path.join(root_dir, date_str, "Among_Us_{} ({}).mp4".format(date_str, round_num))


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    VoteScreen(cv2.imread(r"F:\Videos\Among Us\Apr-29\round_2\meeting_1.bmp"))
    for round_num in range(2, 8):
        se = SceneExtractor(round_num=round_num, date_str="Apr-29")
        se.calculate_all(force_recalculate=True)
    for round_num in range(2, 8):
        se = SceneExtractor(round_num=round_num, date_str="Apr-29")
        se.add_human_details()

    # run_all()

    # root_dir = "F:\\Videos\\Among Us"
    # for item in os.listdir(root_dir):
    #     if os.path.isdir(os.path.join(root_dir, item)):
    #         print("Checking path {}".format(os.path.join(root_dir, item)))
    #         date_str = item
    #         filepath_no_number = os.path.join(root_dir, date_str, "Among_Us_{}.mp4".format(date_str))
    #         round_num = 1
    #         filepath_numbered = os.path.join(root_dir, date_str, "Among_Us_{} ({}).mp4".format(date_str, round_num))
    #         if os.path.exists(filepath_no_number) and not os.path.exists(filepath_numbered):
    #             os.rename(filepath_no_number, filepath_numbered)
    #         while os.path.exists(filepath_numbered):
    #             print("Processing round {}".format(round_num))
    #             print("filepath: {}".format(filepath_numbered))
    #             se = SceneExtractor(round_num=round_num, date_str=date_str)
    #             se.export_round_details()
    #             round_num += 1
    #             filepath_numbered = os.path.join(root_dir, date_str, "Among_Us_{} ({}).mp4".format(date_str, round_num))

    # for r in range(1, 6):
    #     se = SceneExtractor(round_num=r, date_str="Apr-15")
    #     se.export_round_details()

# started 14:28:30ish
