import cv2
from datetime import date
import json
import os


class SceneExtractor:
    def __init__(self, round_num, date_str=None):
        if date_str is None:
            date_str = date.today().strftime("%b-%d")
        self.date_str = date_str
        self.round = round_num
        self.src_folder = "F:/Videos/Among Us/{d}/".format(d=date_str)
        self.dest_folder = self.src_folder + "round_{}/".format(round_num)
        self.src_filename = "Among_Us_{d} ({r})".format(d=date_str, r=round_num)
        self.vidcap = cv2.VideoCapture(self.src_folder + self.src_filename + ".mp4")
        self.meetings = []
        self.general_round_info = {
            "version": "1.0.0",
            "round_start": 0,
            "round_end": None,
            "meetings": []
        }

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
                                  mean_tol=0.1,
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
        return image

    def find_meeting_timestamps(self):
        print("searching for meetings")
        if len(self.meetings) > 0:
            return self.meetings
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
                    self.meetings = meetings
                    return meetings

            # print("transition found between {} and {}, narrowing search".format(low, high))
            # low is now not a meeting but high is, use binary search to hone in
            low, high = self.timestamp_binary_search(self.is_meeting, low, high, 1000)
            # while high - low > 1:
            #     mid = (high + low) / 2
            #     mid_meeting = self.is_meeting(timestamp=mid)
            #     if mid_meeting == low_meeting:
            #         # print(">= {}".format(mid))
            #         low = mid
            #     else:
            #         # print("<= {}".format(mid))
            #         high = mid

            # print("transition is between {} and {}".format(low, high))
            if high_meeting:
                # this is the start of the meeting
                meeting_num += 1
                meeting_details = {
                    "order": meeting_num,
                    "start": high,
                    "end": None,
                    "reporter": None,
                    "alive": [],
                    "dead": [],
                    "new_dead": [],
                    "votes": [],
                    "result": None
                }
                print("Meeting {} start: {}".format(meeting_num, self.format_ts(high)))
            else:
                meeting_details["end"] = low
                meetings.append(meeting_details.copy())
                meeting_details = {}
                print("Meeting {} end: {}".format(meeting_num, self.format_ts(low)))

            low = high
            low_meeting = high_meeting

    def find_round_start(self):
        print("Finding round start time")
        # TODO: do a binary search bounded by 0 and first meeting to leave the dropship. Final dropship ts gives start
        #  time for linear search for start
        lower_bound = 0
        upper_bound = 3600000
        if len(self.meetings) > 0:
            # set upper bound of timestamps to search to the start time of the first meeting
            upper_bound = self.meetings[0]["start"]
        else:
            print("WARNING: no meeting data so round start search is high-unbounded")
        # the search condition for start screen is 3.2 seconds prior to the search timestamp
        ts = lower_bound + 3200
        while not self.is_game_start(ts) and ts <= upper_bound:
            ts += 1000

        if not self.is_game_start(ts):
            print("WARNING: start could not be identified, assuming round was already started")
            self.general_round_info["round_start"] = 0
            return

        # get closer to the end of the start screen animation
        if self.is_game_start(ts + 500):
            ts += 250
        else:
            ts -= 250

        self.general_round_info["round_start"] = ts

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

    def find_round_end(self):
        print("searching for round end screen")
        # get the bounds
        if len(self.meetings) > 0:
            lower_bound = self.meetings[-1]["end"]
        else:
            print("WARNING: no meeting data available so round end search is bounded only by start/end of video")
            lower_bound = 0
        # get video end ts
        upper_bound = self.get_video_length() - 1000

        # check lower bound is not in dropship
        while self.is_dropship(lower_bound):
            # step forward 15 seconds
            lower_bound += 15000
            if lower_bound >= upper_bound:
                print("WARNING: could not find a non-dropship frame to start from")
                self.general_round_info["round_end"] = upper_bound
                return

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
                self.general_round_info["round_end"] = upper_bound
                print("WARNING: Could not find end game")
                return

        print("end game found: {}".format(self.format_ts(end_ts)))
        self.general_round_info["round_end"] = end_ts

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

    def export_round_details(self, write_only=False, overwrite=False):
        output_json_filename = self.dest_folder + "round_{}_details.json".format(self.round)
        if (not overwrite) \
                and os.path.exists(output_json_filename) \
                and json.load(open(output_json_filename, "r")).get("version") == self.general_round_info["version"]:
            print("Video from {} round {} has already been analysed with the latest version; skipping".format(
                self.date_str, self.round
            ))
            return

        # calculate
        if not write_only:
            print("searching video for key frames")
            self.find_meeting_timestamps()
            if len(self.meetings) == 0:
                print("WARNING: meeting search failed to return any results, skipping round")
                return
            self.find_round_start()
            self.find_round_end()

        # gather
        combined_info = self.general_round_info.copy()
        combined_info["meetings"] = self.meetings

        # export
        print("exporting details")
        if not os.path.exists(self.dest_folder):
            os.mkdir(self.dest_folder)
        json.dump(combined_info, open(self.dest_folder + "round_{}_details.json".format(self.round), "w+"),
                  indent=4)
        # print start screen
        cv2.imwrite(self.dest_folder + "round_{}_start.jpg".format(self.round),
                    self.get_screenshot_at(combined_info["round_start"]))
        # print end screen
        cv2.imwrite(self.dest_folder + "round_{}_end.jpg".format(self.round),
                    self.get_screenshot_at(combined_info["round_end"]))
        # print meeting start / ends. In future starts can be removed but leaving in for now for visual verification
        for meeting in self.meetings:
            cv2.imwrite(self.dest_folder + "round_{}_meeting_start_{}.jpg".format(self.round, meeting["order"]),
                        self.get_screenshot_at(meeting["start"]))
            cv2.imwrite(self.dest_folder + "round_{}_meeting_end_{}.jpg".format(self.round, meeting["order"]),
                        self.get_screenshot_at(meeting["end"]))
