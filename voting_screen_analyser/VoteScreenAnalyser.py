import json
import cv2
import os
import re


class VoteScreen:
    def __init__(self, image):
        self.locations = json.load(open("vote_screen_locations.json", "r"))
        self.comparators = json.load(open("colours.json", "r"))
        self.full_image = image
        self.segments = self.segment_image()

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
                "votes": votes,
                "vote_players": vote_players
            })
        skip_votes = self.get_sub_image(full, "skip_votes")
        skip_players = [self.get_sub_image(skip_votes, location=vp_loc) for vp_loc in self.locations["votes_players"]]
        return {
            "full_image": full,
            "grid_rows": rows,
            "skip_votes": skip_votes,
            "skip_players": skip_players
        }

    def get_reporter(self):
        reporter_segments = [row["reporter"] for row in self.segments["grid_rows"]]
        for i in range(len(reporter_segments)):
            rep_seg = reporter_segments[i]
            sample_img = self.get_sub_image(rep_seg, "reporter_check")
            sample = self.get_colour_sample(sample_img)
            result = self.evaluate_sample(sample, "reporter")
            print(str(sample) + "  --> " + str(result))
            if result:
                return i

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


if __name__ == '__main__':
    full_image = cv2.imread(r"F:\Videos\Among Us\Apr-03\round_1\round_1_meeting_end_2.jpg")
    vs = VoteScreen(full_image)
    print(vs.get_reporter())
    # vs.print_segments(vs.segments)
    # vs.print_composite(r"C:\Users\Ben\PycharmProjects\AmongUs\voting_screen_analyser\segments",
    #                    r"_grid_rows-[0-9]_full_row.jpg",
    #                    "rows_composite")
