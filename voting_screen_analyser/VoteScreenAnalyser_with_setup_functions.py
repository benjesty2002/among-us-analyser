import json
import cv2
import os
import re
import numpy as np


class VoteScreen:
    def __init__(self, image):
        self.locations = json.load(open("../vote_screen_locations.json", "r"))
        self.comparators = json.load(open("../colours.json", "r"))
        self.full_image = image
        self.segments = self.segment_image()
        colours = {}
        for pic_type in self.comparators["owner_colour"].keys():
            colours[pic_type] = np.array(
                [[510, 510, 510]] + [col[:3] for col in self.comparators["owner_colour"][pic_type].values()]
            )
        self.colours = colours
        self.colour_names = list(self.comparators["owner_colour"]["rapa"].keys())
        self.summary = {
            "rows": self.analyse_all_rows(),
            "skips": self.analyse_skip_votes()
        }

    def segment_image(self):
        full = self.full_image
        rows = []
        for row_loc in self.locations["player_grid_rows"]:
            row = self.get_sub_image(full, location=row_loc)
            owner = self.get_sub_image(row, "row_owner")
            reporter = self.get_sub_image(row, "row_reporter")
            votes = self.get_sub_image(row, "row_votes")
            vote_players = [self.get_sub_image(votes, location=vp_loc) for vp_loc in self.locations["votes_players"]]
            rows.append({
                "full_row": row,
                "owner": owner,
                "reporter": reporter,
                "votes": vote_players
            })
        skip_votes = self.get_sub_image(full, "skip_votes")
        skip_players = [self.get_sub_image(skip_votes, location=vp_loc) for vp_loc in self.locations["votes_players"]]
        return {
            "full_image": full,
            "grid_rows": rows,
            "skip_votes": skip_players
        }

    def analyse_skip_votes(self):
        # check if recorder is alive
        ra = self.is_recorder_alive()
        ra_str = "ra" if ra else "rd"

        # get skip votes
        votes = []
        for vote_img in self.segments["skip_votes"]:
            col_counts = self.count_colour_pixels(vote_img, self.colours[ra_str + "pa"])
            max_pixels = np.max(col_counts)
            if max_pixels == 0:
                break
            col_ind = np.argmax(col_counts)
            col_name = self.colour_names[col_ind]
            votes.append(col_name)

        return votes

    def analyse_all_rows(self):
        # check if recorder is alive
        ra = self.is_recorder_alive()
        ra_str = "ra" if ra else "rd"

        rows_info = []

        # for each row
        rows = self.segments["grid_rows"]
        for row_num in range(10):
            # TODO: check if the row contains a player
            player_present_sample = self.get_colour_sample(rows[row_num]["full_row"])
            present = self.evaluate_sample(player_present_sample, "player_present")
            if not present:
                break

            # check if player was the reporter
            reporter = self.is_reporter(rows[row_num])

            # check if player is alive
            alive_check_segment = self.get_sub_image(rows[row_num]["full_row"], "alive_check")
            alive_check_sample = self.get_colour_sample(alive_check_segment)
            alive = self.evaluate_sample(alive_check_sample, "alive")
            pa_str = "pa" if alive else "pd"

            # get player colour
            player_image = rows[row_num]["owner"]
            image_type = ra_str + pa_str
            segment_location = self.locations["owner_colour_check"][image_type]
            segment = self.get_sub_image(player_image, location=segment_location)
            col_counts = self.count_colour_pixels(segment, self.colours[image_type], 25)
            # if recorder is dead and this is row 9 (index 8) adjust for the additional
            # black and brown from screen crack
            if not ra and row_num == 8:
                col_counts[0] -= 68
                col_counts[2] -= 38
            owner_col = self.colour_names[np.argmax(col_counts)]

            # get votes for the player
            votes = []
            if alive:
                for vote_img in rows[row_num]["votes"]:
                    col_counts = self.count_colour_pixels(vote_img, self.colours[ra_str + "pa"])
                    max_pixels = np.max(col_counts)
                    col_ind = np.argmax(col_counts)
                    col_name = self.colour_names[col_ind]
                    if max_pixels > 0:
                        votes.append(col_name)

            # summarise info
            rows_info.append({
                "colour": owner_col,
                "reporter": reporter,
                "alive": alive,
                "votes_for": votes
            })

        return rows_info

    def is_recorder_alive(self):
        ra_segment = self.get_sub_image(self.full_image, "recorder_alive_check")
        return self.evaluate_sample(self.get_colour_sample(ra_segment), "recorder_alive")

    def is_reporter(self, row_dict):
        rep_seg = row_dict["reporter"]
        sample_img = self.get_sub_image(rep_seg, "reporter_check")
        sample = self.get_colour_sample(sample_img)
        print(sample)
        return self.evaluate_sample(sample, "reporter")

    @staticmethod
    def print_segments(segments, filename="segments/"):
        for key, value in segments.items():
            print(key + " " + str(type(value)))
            if type(value) == dict:
                VoteScreen.print_segments(value, filename + "_" + key)
            elif type(value) == list:
                for i in range(len(value)):
                    if type(value[i]) == dict:
                        VoteScreen.print_segments(value[i], filename + "_" + key + "-" + str(i))
                    else:
                        pass
                        # cv2.imwrite(filename + "_" + key + "_" + str(i) + ".jpg", value[i])
            else:
                if key in ["reporter"]:
                    cv2.imwrite(filename + "_" + key + ".jpg", value)

    def get_sub_image(self, image, location_name=None, location=None):
        if location is None:
            location = self.locations[location_name]
        return image[location[0]:location[1], location[2]:location[3]]

    @staticmethod
    def get_colour_sample(image):
        # cv2.imwrite("temp.jpg", image)
        mean, std = cv2.meanStdDev(image)
        return [val[0] for val in mean] + [val[0] for val in std]

    def evaluate_sample(self, sample, comparator_name):
        comparator = self.comparators[comparator_name]
        if comparator["type"] == "match":
            for i in range(6):
                if abs(sample[i] - comparator["expectation"][i]) > comparator["tolerance"][i]:
                    return False
            return True

    @staticmethod
    def print_composite(folder, filename_pattern, outfile):
        images = []
        for file in os.listdir(folder):
            if re.match(filename_pattern, file):
                images.append(cv2.imread(os.path.join(folder, file)))

        composite_max = images[0]
        composite_avg = images[0] / len(images)
        composite_min = images[0]
        for i in range(1, len(images)):
            composite_max = cv2.max(composite_max, images[i])
            composite_avg += images[i] / len(images)
            composite_min = cv2.min(composite_min, images[i])

        cv2.imwrite(outfile + "_max.jpg", composite_max)
        cv2.imwrite(outfile + "_avg.jpg", composite_avg)
        cv2.imwrite(outfile + "_min.jpg", composite_min)

    @staticmethod
    def count_colour_pixels(image, colours, var=10):
        # takes image input and an n by 3 array of colours

        # calculate the distance from each pixel to each colour
        pdist = np.linalg.norm(image[:, :, None] - colours[None, None, :], axis=3)
        # set the first colour option to the minimum allowed distance to become the default colour
        pdist[:, :, 0] = var
        colours[0] = [255, 255, 255]
        # find the index of the minimum distance colour for each pixel
        pal_img = np.argmin(pdist, axis=2)
        # find how many pixels match each colour definition
        col_counts = [np.sum(pal_img == i) for i in range(1, len(colours))]
        return col_counts

    def get_colour_definitions(self):
        col_defs = {}
        root = r"C:\Users\Ben\PycharmProjects\AmongUs\voting_screen_analyser\player_pic_groups"
        for pic_type in os.listdir(root):
            col_defs[pic_type] = {}
            for file in os.listdir(os.path.join(root, pic_type)):
                col_name = file[:len(file) - 4]
                image = cv2.imread(os.path.join(root, pic_type, file))
                segment = self.get_sub_image(image, "owner_colour_sample")
                col_numeric = self.get_colour_sample(segment)
                col_defs[pic_type][col_name] = col_numeric
        print(json.dumps(col_defs, indent=4))
        print(col_defs)

    def check_colour_matching(self):
        root = r"C:\Users\Ben\PycharmProjects\AmongUs\voting_screen_analyser\player_pics"
        colours = {}
        for pic_type in self.comparators["owner_colour"].keys():
            colours[pic_type] = np.array(
                [[510, 510, 510]] + [col[:3] for col in self.comparators["owner_colour"][pic_type].values()]
            )
        colour_names = list(self.comparators["owner_colour"]["rapa"].keys())
        results = {}
        for colour in colour_names:
            results[colour] = {"rapa": {"success": 0, "failure": 0},
                               "rdpa": {"success": 0, "failure": 0},
                               "rapd": {"success": 0, "failure": 0},
                               "rdpd": {"success": 0, "failure": 0}}
            for file in os.listdir(os.path.join(root, colour)):
                image_type = file[:4]
                image = cv2.imread(os.path.join(root, colour, file))
                segment = self.get_sub_image(image, location=self.locations["owner_colour_check"][image_type])
                col_counts = self.count_colour_pixels(segment, colours[image_type], 25)
                determined_col = colour_names[np.argmax(col_counts)]
                if determined_col == colour:
                    results[colour][file[:4]]["success"] += 1
                else:
                    print(os.path.join(root, colour, file) + " != " + determined_col)
                    print(col_counts)
                    results[colour][file[:4]]["failure"] += 1
            print(colour + "\t" + str(results[colour]))


def export_owner_pics():
    pattern = "round_([0-9]+)_meeting_end_([0-9]+)"
    for root, dirs, files in os.walk("F:/Videos/Among Us"):
        for file in files:
            m = re.search("round_([0-9]+)_meeting_end_([0-9]+).jpg", file)
            if re.match(pattern, file):
                round_num, meeting_num = re.search(pattern, file).group(1, 2)
                date = re.search("([A-Z][a-z]{2}-[0-9]{1,2})", root).group(1)

                image = cv2.imread(os.path.join(root, file))
                vs = VoteScreen(image)

                ra_segment = vs.get_sub_image(image, "recorder_alive_check")
                recorder_alive = vs.evaluate_sample(vs.get_colour_sample(ra_segment), "recorder_alive")
                ra_str = "ra" if recorder_alive else "rd"

                for i in range(10):
                    row_dict = vs.segments["grid_rows"][i]
                    # check if alive
                    alive_check_segment = vs.get_sub_image(row_dict["full_row"], "alive_check")
                    alive_check_sample = vs.get_colour_sample(alive_check_segment)
                    # print(alive_check_sample)
                    row_alive = vs.evaluate_sample(alive_check_sample, "alive")
                    pa_str = "pa" if row_alive else "pd"

                    player_img = vs.segments["grid_rows"][i]["owner"]
                    outfile = "player_pics/{}{}_{}_round{}_meet{}_row{}.jpg".format(ra_str, pa_str, date, round_num,
                                                                                    meeting_num, i)
                    cv2.imwrite(outfile, player_img)
                    print(outfile)


if __name__ == '__main__':
    full_image = cv2.imread(r"F:\Videos\Among Us\Apr-03\round_6\round_6_meeting_end_2.jpg")
    vs = VoteScreen(full_image)

    print(json.dumps(vs.summary, indent=4))
    #
    # rnum = 0
    # for row in vs.segments["grid_rows"]:
    #     rnum += 1
    #     cv2.imwrite("segments/votes/row{}.bmp".format(rnum), row["full_row"])
    #     row_votes = vs.get_sub_image(row["full_row"], "row_votes")
    #     cv2.imwrite("segments/votes/row{}_votes.bmp".format(rnum), row_votes)
    #     votenum = 0
    #     for vote in row["votes"]:
    #         votenum += 1
    #         cv2.imwrite("segments/votes/r{}v{}.bmp".format(rnum, votenum), vote)
    #
    # locs = []
    # for i in range(10):
    #     locs.append([0, 30, 36 * i, 36 * (i + 1)])
    # print(locs)
    #
    # player_img = cv2.imread(
    #     r"C:\Users\Ben\PycharmProjects\AmongUs\voting_screen_analyser\player_pics\lime\rdpd_Apr-15_round6_meet4_row8.jpg")
    # segment = vs.get_sub_image(player_img, location=vs.locations["owner_colour_check"]["rdpd"])
    # col_counts = vs.count_colour_pixels(segment, vs.colours["rdpd"], 25)
    # print(col_counts)
    #
    # vs.check_colour_matching()
    #
    # player_img = cv2.imread(
    #     r"C:\Users\Ben\PycharmProjects\AmongUs\voting_screen_analyser\player_pics\purple\rapa_Apr-03_round8_meet2_row2.jpg")
    # vs.get_sub_image(player_img, "owner_colour_check")
    # print(vs.get_colour_sample(vs.get_sub_image(player_img, "owner_colour_check")))
    #
    # colours = [[510, 510, 510]] + [col[:3] for col in vs.comparators["live_colour"]["options"].values() if len(col) > 0]
    # colours = np.array(colours)
    # colours = np.array([
    #     [510, 510, 510],
    #     [0, 0, 0],
    #     [72.4375, 49.0625, 180.9375],
    #     [209.375, 80.0625, 63.5625],
    #     [95.0625, 159.8125, 67.8125],
    #     [194.6875, 98.5625, 214.875],
    #     [72.8125, 141.5625, 218.25],
    #     [239.375, 219.0, 205.9375],
    #     [178.1875, 75.75, 112.875],
    #     [108.9375, 252.625, 116.75],
    #     [255, 255, 255]
    # ])

    # img2 = vs.count_colour_pixels(player_img, colours, 10)
    # cv2.imwrite("img2.bmp", img2)
    # rac = vs.get_sub_image(full_image, "recorder_alive_check")
    # print(vs.get_colour_sample(rac))

    #
    # for row in vs.segments["grid_rows"]:
    #     print("\n")
    #     vs.perform_row_checks(row)

    # export_owner_pics()
    # print(vs.get_reporter())
    # vs.print_segments(vs.segments)
    # vs.print_composite(r"C:\Users\Ben\PycharmProjects\AmongUs\voting_screen_analyser\segments",
    #                    r"_grid_rows-[0-9]_owner.jpg",
    #                    "owner_composite_")

# TODO: define sample location for each of rapd, rdpa, rdpd, then extract the colour definition for each colour
