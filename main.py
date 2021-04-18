from SceneExtractor import SceneExtractor
import os

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    root_dir = "F:\\Videos\\Among Us"
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

    # for r in range(1, 6):
    #     se = SceneExtractor(round_num=r, date_str="Apr-15")
    #     se.export_round_details()

# started 14:28:30ish
