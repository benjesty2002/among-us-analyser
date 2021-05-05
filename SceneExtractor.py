import cv2
from datetime import date
import json
import os

import DataFormatter
from VoteScreenAnalyser import VoteScreen


class SceneExtractor:
    def __init__(self, round_num, date_str=None):
        if date_str is None:
            date_str = date.today().strftime("%b-%d")
        src_folder = "F:/Videos/Among Us/{d}/".format(d=date_str)
        dest_folder = src_folder + "round_{}/".format(round_num)
        if not os.path.exists(dest_folder):
            os.mkdir(dest_folder)
        src_filename = "Among_Us_{d} ({r}).mp4".format(d=date_str, r=round_num)
        self.vidcap = cv2.VideoCapture(src_folder + src_filename)
        self.file_paths = {
            "timestamps": dest_folder + "timestamps.json",
            "meeting_screenshots": dest_folder + "meeting_{}.bmp",
            "meeting_raw_data": dest_folder + "meetings.json",
            "round_start": dest_folder + "round_start.bmp",
            "round_end": dest_folder + "round_end.bmp",
            "summary": dest_folder + "summary.json",
            "human_additions": dest_folder + "human_additions.json"
        }
        self.version = "1.1.1"
        self.is_stream = False

    @staticmethod
    def array_3_match(arr1, arr2, tol):
        for i in range(3):
            if abs(arr1[i][0] - arr2[i][0]) > tol:
                return False
        return True

    def print_metric_range(self, bounds, ts_start, ts_end, ts_step=100):
        img = self.get_screenshot_at(ts_start)
        segment = img[bounds[0]:bounds[1], bounds[2]:bounds[3]]
        cv2.imwrite("start.jpg", segment)
        mean, std = cv2.meanStdDev(segment)
        mins = [round(val[0], 2) for val in mean] + [round(val[0], 2) for val in std]
        maxes = mins.copy()

        for ts in range(ts_start, ts_end, ts_step):
            img = self.get_screenshot_at(ts)
            segment = img[bounds[0]:bounds[1], bounds[2]:bounds[3]]
            mean, std = cv2.meanStdDev(segment)
            nums = [round(val[0], 2) for val in mean] + [round(val[0], 2) for val in std]
            print("TS: {}\t{}".format(self.format_ts(ts), str(nums)))
            mins = [min(mins[i], nums[i]) for i in range(6)]
            maxes = [max(maxes[i], nums[i]) for i in range(6)]

        cv2.imwrite("end.jpg", segment)
        print()
        print("MIN: {}".format(str(mins)))
        print("MAX: {}".format(str(maxes)))
        print("RANGE: {}".format(str([maxes[i] - mins[i] for i in range(6)])))

    def check_segment(self, timestamp, bounds, expected_mean, mean_tol, expected_std, std_tol):
        img = self.get_screenshot_at(timestamp)
        segment = img[bounds[0]:bounds[1], bounds[2]:bounds[3]]
        mean, std = cv2.meanStdDev(segment)
        # print(str(mean) + "   " + str(std))
        mean_pass = self.array_3_match(mean, expected_mean, mean_tol)
        std_pass = self.array_3_match(std, expected_std, std_tol)
        return mean_pass and std_pass

    def is_meeting(self, timestamp):
        # check for solid grey rectangles (the right hand border of the voting screen). If top is not a match, check
        # the bottom. My mouse may have been over the top panel and messed up the std
        top_panel_bounds = [35, 313, 1070, 1125]
        bottom_panel_bounds = [389, 671, 1070, 1125]
        for bounds in [top_panel_bounds, bottom_panel_bounds]:
            if self.check_segment(timestamp=timestamp,
                                  bounds=bounds,
                                  expected_mean=[[162.], [150.], [142.]],
                                  mean_tol=3,
                                  expected_std=[[0.], [0.], [0.]],
                                  std_tol=1):
                return True
        return False

    def is_game_end(self, timestamp):
        # check for presence of the "exit" or "return to lobby" buttons
        # exit button check
        if self.check_segment(timestamp=timestamp,
                              bounds=[525, 700, 15, 165],
                              expected_mean=[[68.], [68.3], [75.9]],
                              mean_tol=0.5,
                              expected_std=[[79.8], [79.4], [83.9]],
                              std_tol=0.5):
            return True
        # play again button check
        if self.check_segment(timestamp=timestamp,
                              bounds=[510, 710, 1110, 1255],
                              expected_mean=[[66.], [66.], [72.]],
                              mean_tol=2,
                              expected_std=[[79.4], [79.6], [83.4]],
                              std_tol=1):
            return True
        return False

    def is_game_start(self, timestamp):
        # check for the "SHHHHH!" picture 3.2 seconds prior to timestamp. This image is shown for 1.6 seconds
        if self.check_segment(timestamp=timestamp - 3200,
                              bounds=[35, 585, 335, 940],
                              expected_mean=[[37.], [63.], [138.]],
                              mean_tol=4,
                              expected_std=[[49.], [83.5], [94.5]],
                              std_tol=2):
            return True
        return False

    def is_dropship(self, timestamp):
        # check for the "private" logo (possibly also the white player marker if necessary)
        # "PRIVATE" check
        if self.check_segment(timestamp=timestamp,
                              bounds=[635, 670, 400, 520],
                              expected_mean=[[93.7], [86.9], [142.5]],
                              mean_tol=1,
                              expected_std=[[73.1], [75.8], [78.3]],
                              std_tol=1):
            return True
        return False

    def get_screenshot_at(self, timestamp):
        self.vidcap.set(cv2.CAP_PROP_POS_MSEC, timestamp)
        success, image = self.vidcap.read()
        if not success:
            raise RuntimeError("end of stream")
        if self.is_stream:
            # scale the image
            top = 40
            bottom = 669
            left = 5
            right = 1123
            au_segment = image[top:bottom, left:right]
            image = cv2.resize(au_segment, (1280, 720), cv2.INTER_AREA)
            # cv2.imshow("rescaled", image)
            # cv2.waitKey(0)
            # cv2.destroyAllWindows()
        return image

    def check_existing_file_version(self, file_path):
        if not os.path.exists(file_path):
            return False, None
        if file_path[-4:] == ".bmp":
            return True, None
        json_data = json.load(open(file_path, "r"))
        return json_data.get("version") == self.version, json_data

    def find_meeting_timestamps(self):
        print("searching for meetings")

        blind_step = 15000
        low = 0
        low_meeting = False
        high = 0
        high_meeting = self.is_meeting(timestamp=0)
        meeting_num = 0
        meeting_details = {}
        meetings = []

        while True:
            # print("finding next meeting transition")
            # blind step forward to first meeting transition requested in scene_types
            while high_meeting == low_meeting:
                low = high
                low_meeting = high_meeting
                high += blind_step
                # print("stepping forward 15s to {}".format(high))
                try:
                    high_meeting = self.is_meeting(timestamp=high)
                except RuntimeError:
                    # end of video hit
                    return meetings

            # low is now not a meeting but high is, or vice versa, use binary search to hone in
            low, high = self.timestamp_binary_search(self.is_meeting, low, high, 1000)

            if high_meeting:
                # this is the start of the meeting
                meeting_num += 1
                meeting_details = {
                    "order": meeting_num,
                    "start": high,
                    "end": None
                }
                print("Meeting {} start: {}".format(meeting_num, self.format_ts(high)))
            else:
                meeting_details["end"] = low
                meetings.append(meeting_details.copy())
                meeting_details = {}
                print("Meeting {} end: {}".format(meeting_num, self.format_ts(low)))
                cv2.imwrite(self.file_paths["meeting_screenshots"].format(meeting_num), self.get_screenshot_at(low))

            low = high
            low_meeting = high_meeting

    def find_round_start(self, first_meeting_start):
        print("Finding round start time")
        # TODO: do a binary search bounded by 0 and first meeting to leave the dropship. Final dropship ts gives start
        #  time for linear search for start
        lower_bound = 0
        if first_meeting_start is None:
            print("WARNING: no meeting data given so round start search is high-unbounded")
            upper_bound = 3600000
        else:
            upper_bound = first_meeting_start

        # the search condition for start screen is 3.2 seconds prior to the search timestamp
        ts = lower_bound + 3200
        while not self.is_game_start(ts) and ts <= upper_bound:
            ts += 1000

        if not self.is_game_start(ts):
            print("WARNING: start could not be identified, assuming round was already started")
            return None

        # get closer to the end of the start screen animation
        if self.is_game_start(ts + 500):
            ts += 250
        else:
            ts -= 250

        cv2.imwrite(self.file_paths["round_start"], self.get_screenshot_at(ts))
        return ts

    def get_video_length(self):
        # get number of frames in video & divide by frame rate
        frame_count = int(self.vidcap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = self.vidcap.get(cv2.CAP_PROP_FPS)
        end_seconds = frame_count / fps
        return end_seconds * 1000

    @staticmethod
    def format_ts(ts_in):
        ts_in = int(ts_in)
        ts = ts_in
        ms = ts % 1000
        ts = int(ts / 1000)
        secs = ts % 60
        mins = int(ts / 60)
        return "{:02d}:{:02d}.{} ({})".format(mins, secs, ms, ts_in)

    def find_round_end(self, final_meeting_end):
        print("searching for round end screen")
        # get the bounds
        if final_meeting_end is None:
            print("WARNING: no meeting data available so round end search is bounded only by start/end of video")
            lower_bound = 0
        else:
            lower_bound = final_meeting_end

        # get video end ts
        upper_bound = self.get_video_length() - 100

        # step back if the end is out of bounds
        self.vidcap.set(cv2.CAP_PROP_POS_MSEC, upper_bound)
        success, image = self.vidcap.read()
        while not success:
            upper_bound -= 1000
            self.vidcap.set(cv2.CAP_PROP_POS_MSEC, upper_bound)
            success, image = self.vidcap.read()

        # check lower bound is not in dropship
        while self.is_dropship(lower_bound):
            # step forward 15 seconds
            lower_bound += 15000
            if lower_bound >= upper_bound:
                print("WARNING: could not find a non-dropship frame to start from")
                return

        # if I wasn't quick enough stopping the recording, try 15 seconds prior
        if not self.is_dropship(upper_bound) and self.is_dropship(upper_bound - 15000):
            upper_bound -= 15000
        # binary search if upper bound is dropship
        if self.is_dropship(upper_bound):
            last_non_dropship, first_dropship = self.timestamp_binary_search(self.is_dropship, lower_bound, upper_bound,
                                                                             end_precision=1000)
            print("returned to dropship between {} and {}".format(self.format_ts(last_non_dropship),
                                                                  self.format_ts(first_dropship)))
        else:
            print("WARNING: Video did not end in dropship so binary search for end is impossible")
            print("Attempting linear search from end of video (slow)")
            first_dropship = upper_bound

        # linear search for end screen back from first_dropship
        end_ts = first_dropship - 500
        while not self.is_game_end(end_ts):
            end_ts -= 500
            if end_ts < lower_bound:
                print("WARNING: Could not find end game")
                return None

        print("end game found: {}".format(self.format_ts(end_ts)))
        cv2.imwrite(self.file_paths["round_end"], self.get_screenshot_at(end_ts))
        return end_ts

    @staticmethod
    def timestamp_binary_search(scene_test, ts_low, ts_high, end_precision):
        print("binary search between {} and {} to precision of {}".format(
            SceneExtractor.format_ts(ts_low), SceneExtractor.format_ts(ts_high), int(end_precision)))
        if ts_low > ts_high:
            raise RuntimeError("start time later than end time")
        scene_low = scene_test(ts_low)
        scene_high = scene_test(ts_high)
        if scene_low == scene_high:
            raise RuntimeError("start and end timestamps return the same scene result")

        while ts_high - ts_low > end_precision:
            ts_mid = (ts_low + ts_high) / 2
            scene_mid = scene_test(ts_mid)

            if scene_mid == scene_high:
                ts_high = ts_mid
            else:
                ts_low = ts_mid

        return ts_low, ts_high

    def find_timestamps(self, force_recalculate=False):
        file_path = self.file_paths["timestamps"]
        if not force_recalculate:
            latest_version, timestamps = self.check_existing_file_version(file_path)
            if latest_version:
                return timestamps

        # get start / end times of each meeting
        meeting_timestamps = self.find_meeting_timestamps()
        if len(meeting_timestamps) == 0:
            raise RuntimeError("No meetings found")

        # get round start / end times
        if len(meeting_timestamps) > 0:
            first_meeting_start = meeting_timestamps[0]["start"]
            final_meeting_end = meeting_timestamps[-1]["end"]
        else:
            first_meeting_start = None
            final_meeting_end = None
        round_start = self.find_round_start(first_meeting_start)
        round_end = self.find_round_end(final_meeting_end)

        timestamps = {
            "version": self.version,
            "round_start": round_start,
            "round_end": round_end,
            "meetings": meeting_timestamps
        }
        json.dump(timestamps, open(file_path, "w+"), indent=4)
        return timestamps

    def extract_meeting_data(self, meeting_timestamps, force_recalculate=False):
        file_path = self.file_paths["meeting_raw_data"]
        if not force_recalculate:
            latest_version, meeting_data = self.check_existing_file_version(file_path)
            if latest_version:
                return meeting_data["meetings"]

        # get info from individual meetings
        for meeting in meeting_timestamps:
            meeting["screenshot_summary"] = VoteScreen(self.get_screenshot_at(meeting["end"])).summary

        meeting_data = {
            "version": self.version,
            "meetings": meeting_timestamps
        }
        json.dump(meeting_data, open(file_path, "w+"), indent=4)
        return meeting_timestamps

    def format_data(self, timestamps, meeting_data, force_recalculate=False):
        file_path = self.file_paths["summary"]
        if not force_recalculate:
            latest_version, formatted_data = self.check_existing_file_version(file_path)
            if latest_version:
                return formatted_data

        formatted_data = DataFormatter.summarise_data(timestamps["round_start"], timestamps["round_end"], meeting_data)
        formatted_data["version"] = self.version
        json.dump(formatted_data, open(file_path, "w+"), indent=4)
        return formatted_data

    def calculate_all(self, human_input=False, force_recalculate=False):
        # identify key timestamps
        timestamps = self.find_timestamps(force_recalculate)

        # get info from individual meetings
        meeting_data = self.extract_meeting_data(timestamps["meetings"], force_recalculate)

        # combine & format the data
        formatted_data = self.format_data(timestamps, meeting_data, force_recalculate)

        if human_input:
            formatted_data = self.add_human_details(formatted_data)

        return formatted_data

    def add_human_details(self, round_summary=None):
        # check if responses are already present
        if os.path.exists(self.file_paths["human_additions"]):
            human_additions = json.load(open(self.file_paths["human_additions"], "r"))
            outcome = human_additions.pop("win_condition", None)
            if outcome is None:
                crew_win = human_additions["crew_win"]
            else:
                crew_win = "Y" if outcome[0] == "c" else "N"
            impostors = human_additions.get("impostors")
        else:
            human_additions = {}
            crew_win = None
            impostors = None

        # load raw timestamp info
        timestamps = json.load(open(self.file_paths["timestamps"], "r"))
        round_start = timestamps["round_start"]
        if round_start is None:
            round_start = timestamps["meetings"][0]["end"]
        round_end = timestamps["round_end"]
        if round_end is None:
            round_end = timestamps["meetings"][-1]["end"]

        if round_summary is None:
            round_summary = json.load(open(self.file_paths["summary"], "r"))

        if crew_win is None or impostors is None:
            cv2.imshow("round_start", self.get_screenshot_at(round_start))
            cv2.imshow("round_end", self.get_screenshot_at(round_end))
            cv2.waitKey(0)

        final_meeting = round_summary["meetings"][-1]
        alive_after_final_vote = [player for player in final_meeting["alive"] if player != final_meeting["outcome"]]

        if impostors is None:
            # get impostor colours from human
            impostors = input("Which colours were the impostors? ").lower().replace(" ", "").split(",")
        human_additions["impostors"] = impostors

        # check if the last vote concluded the game
        win_condition = None
        total_alive = len(alive_after_final_vote)
        impostors_alive = 0
        for player in alive_after_final_vote:
            if player in human_additions["impostors"]:
                impostors_alive += 1
        if impostors_alive == (total_alive / 2):
            win_condition = "impostor_vote"
        elif impostors_alive == 0:
            win_condition = "crew_vote"

        # if win condition cannot be determined from the last round & impostors, ask the human
        if win_condition is None:
            if crew_win is None:
                crew_win = input("Did crew win (Yes/No/Unknown)? ")[0].upper()
            win_condition = {"Y": "crew_tasks", "N": "impostor_kill", "U": "unknown"}[crew_win]
        human_additions["win_condition"] = win_condition

        cv2.destroyAllWindows()

        # get human input
        round_summary["impostors"] = human_additions["impostors"]
        round_summary["outcome"] = human_additions["win_condition"]

        json.dump(human_additions, open(self.file_paths["human_additions"], "w+"), indent=4)
        json.dump(round_summary, open(self.file_paths["summary"], "w+"), indent=4)
        return round_summary
