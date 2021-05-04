import json
import cv2
import numpy as np


class VoteScreen:
    def __init__(self, image):
        self.locations = json.load(open("vote_screen_locations.json", "r"))
        self.comparators = json.load(open("colours.json", "r"))
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
            if max_pixels < 30:
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
            # check if the row contains a player
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
                # the 10th vote slot causes issues when reporter is dead. It is unnecessary, so avoid using it
                max_votes = 10 if ra else 9
                for vote_img in rows[row_num]["votes"][:max_votes]:
                    col_counts = self.count_colour_pixels(vote_img, self.colours[ra_str + "pa"])
                    max_pixels = np.max(col_counts)
                    # threshold to avoid black coming up from the mouse or a random line
                    if max_pixels < 30:
                        break
                    col_ind = np.argmax(col_counts)
                    col_name = self.colour_names[col_ind]
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
        return self.evaluate_sample(sample, "reporter")

    def get_sub_image(self, image, location_name=None, location=None):
        if location is None:
            location = self.locations[location_name]
        return image[location[0]:location[1], location[2]:location[3]]

    @staticmethod
    def get_colour_sample(image):
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

# debugging code

# print(sample)
# print(self.evaluate_sample(sample, "reporter"))
# cv2.imshow("reporter_check", sample_img)
# cv2.waitKey(0)
# cv2.destroyAllWindows()
