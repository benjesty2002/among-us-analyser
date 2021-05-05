import cv2

from SceneExtractor import SceneExtractor
from VoteScreenAnalyser import VoteScreen
import os
import json

def convert_colours_to_players(directory, colour_map=None):
    # load the default colour map if one is not provided
    if colour_map is None:
        colour_map = json.load(open("default_player_colours.json", "r"))
    # load the current state of round summary and human additions to this round's data
    human_additions = json.load(open(os.path.join(directory, "human_additions.json"), "r"))
    summary = json.load(open(os.path.join(directory, "summary.json"), "r"))
    # if human has already confirmed colours, use them, else take from colour map & check with human
    player_colours = human_additions.get("player_colours")
    if player_colours is None:
        player_colours = {player_colour: colour_map[player_colour] for player_colour in summary["player_list"]}
        print(json.dumps(player_colours, indent=4))
        cv2.imshow("meeting 1", cv2.imread(os.path.join(directory, "meeting_1.bmp")))
        cv2.waitKey()
        modifications = input("Any changes? (in format col1:name1,col2:name2")
        cv2.destroyAllWindows()
        if len(modifications) > 0:
            for modification in modifications.split(","):
                pair = modification.split(":")
                colour_map[pair[0]] = pair[1]
            player_colours = {player_colour: colour_map[player_colour] for player_colour in summary["player_list"]}
    # add player_colours to the human input file
    human_additions["player_colours"] = player_colours
    json.dump(human_additions, open(os.path.join(directory, "human_additions.json"), "w+"), indent=4)
    # swap out the colours for names & write to new file
    summary_str = json.dumps(summary, indent=4)
    for colour, player in player_colours.items():
        summary_str = summary_str.replace('"{}"'.format(colour), '"{}"'.format(player))
    summary_players = json.loads(summary_str)
    json.dump(summary_players, open(os.path.join(directory, "summary_players.json"), "w+"), indent=4)
    return colour_map

def run_all():
    errors = []
    successes = []
    root_dir = r"F:\Videos\Among Us"
    for date_str in os.listdir(root_dir):
        if os.path.isdir(os.path.join(root_dir, date_str)):
            print("Checking path {}".format(os.path.join(root_dir, date_str)))
            filepath_no_number = os.path.join(root_dir, date_str, "Among_Us_{}.mp4".format(date_str))
            round_num = 1
            filepath_numbered = os.path.join(root_dir, date_str, "Among_Us_{} ({}).mp4".format(date_str, round_num))
            if os.path.exists(filepath_no_number) and not os.path.exists(filepath_numbered):
                os.rename(filepath_no_number, filepath_numbered)
            while os.path.exists(filepath_numbered):
                print("Processing round {}".format(round_num))
                print("filepath: {}".format(filepath_numbered))
                se = SceneExtractor(round_num=round_num, date_str=date_str)
                error_file = os.path.join(root_dir, date_str, "round_{}".format(round_num),
                                          "processing_error_v{}.json".format(se.version))
                if os.path.exists(error_file):
                    error = json.load(open(error_file, "r"))
                else:
                    error = None
                    try:
                        se.calculate_all()
                        successes.append({"round_num": round_num, "date_str": date_str})
                    except Exception as e:
                        error = {
                            "date_str": date_str,
                            "round": round_num,
                            "error": str(e)
                        }
                        json.dump(error, open(error_file, "w+"), indent=4)
                if error is not None:
                    errors.append(error)
                round_num += 1
                filepath_numbered = os.path.join(root_dir, date_str, "Among_Us_{} ({}).mp4".format(date_str, round_num))
    json.dump(errors, open("errors.json", "w+"), indent=4)
    # add impostor & win team details
    for s in successes:
        print(s)
        se = SceneExtractor(**s)
        se.add_human_details()
    # confirm player colours
    prev_round_date = ""
    colour_map = None
    for s in successes:
        print(s)
        directory = os.path.join(root_dir, s["date_str"], "round_{}".format(s["round_num"]))
        if prev_round_date != s["date_str"]:
            colour_map = None
        colour_map = convert_colours_to_players(directory, colour_map)
        prev_round_date = s["date_str"]



# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    # se = SceneExtractor(round_num=1, date_str="Apr-03")
    # se.add_human_details()
    # se.calculate_all(force_recalculate=True)

    run_all()
    # vidcap = cv2.VideoCapture(r"F:\Videos\Among Us\Apr-03\Among_Us_Apr-03 (4).mp4")
    # vidcap.set(cv2.CAP_PROP_POS_MSEC, 0)
    # success, image = vidcap.read()
    # cv2.imwrite("stream_img.bmp", image)
    # VoteScreen(cv2.imread(r"F:\Videos\Among Us\Apr-29\round_7\meeting_4.bmp"))
    # se = SceneExtractor(round_num=7, date_str="Apr-29")
    # se.calculate_all(force_recalculate=True)
    # se.add_human_details()
    # for round_num in range(2, 8):
    #     se = SceneExtractor(round_num=round_num, date_str="Apr-29")
    #     se.calculate_all(force_recalculate=True)
    # for round_num in range(2, 8):
    #     se = SceneExtractor(round_num=round_num, date_str="Apr-29")
    #     se.add_human_details()

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
