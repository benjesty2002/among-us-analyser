import json
from collections import defaultdict


class StatCalculator:
    def __init__(self, combined_summary_file=r"F:\Videos\Among Us\all_summaries.json",
                 combined_summary_file_cols=r"F:\Videos\Among Us\all_summaries_colours.json"):
        self.combined_summaries = json.load(open(combined_summary_file, "r"))
        self.combined_summaries_colours = json.load(open(combined_summary_file_cols, "r"))

    def ranked_impostor_games(self):
        pair_scores = defaultdict(list)
        individuals = defaultdict(lambda: {"pair_sum": 0, "ind_sum": 0, "count": 0, "ind_perf_rounds": 0})
        for date, rounds in self.combined_summaries.items():
            rnum = 0
            for rnd in rounds:
                rnum += 1
                if "error" in rnd:
                    continue
                impostors = rnd["impostors"]
                ind_imp_votes = {i: 0 for i in impostors}
                imp_votes = 0
                total_votes = 0
                for meeting in rnd["meetings"]:
                    for voter, vote in meeting["vote_log"].items():
                        if voter in impostors:
                            continue
                        if vote in impostors:
                            imp_votes += 1
                            ind_imp_votes[vote] += 1
                        total_votes += 1
                pair_scores[int(100 * imp_votes / total_votes)]. \
                    append(" & ".join(impostors) + " ({d}, round {r})".format(d=date, r=rnum))
                for i in impostors:
                    individuals[i]["pair_sum"] += imp_votes
                    individuals[i]["count"] += total_votes
                    individuals[i]["ind_sum"] += ind_imp_votes[i]
                    if ind_imp_votes[i] == 0:
                        individuals[i]["ind_perf_rounds"] += 1

        individuals = {
            player: {
                "individual_average": round(100 * individuals[player]["ind_sum"] / individuals[player]["count"]),
                "partner_average": round(100 * individuals[player]["pair_sum"] / individuals[player]["count"]) -
                                   round(100 * individuals[player]["ind_sum"] / individuals[player]["count"]),
                "ind_perfect_rounds": round(individuals[player]["ind_perf_rounds"])
            }
            for player in sorted(individuals.keys())
        }
        pair_scores.keys()
        pair_scores = {score: pair_scores[score] for score in sorted(pair_scores.keys())}
        return pair_scores, individuals

    def crew_voting_record(self):
        vote_record = defaultdict(
            lambda: {"crew": 0, "impostor": 0, "impostor_points": 0.0, "possible_points": 0.0, "impostor_overruled": 0,
                     "skip": 0, "no_vote": 0})
        for date, rounds in self.combined_summaries.items():
            for rnd in rounds:
                if "error" in rnd:
                    continue
                impostors = rnd["impostors"]
                for meeting in rnd["meetings"]:
                    impostors_alive = len([i for i in impostors if i in meeting["alive"]])
                    total_alive = len(meeting["alive"])
                    hit_score = float(total_alive) / impostors_alive
                    for voter, vote in meeting["vote_log"].items():
                        if voter in impostors:
                            continue
                        minority = vote != meeting["outcome"]
                        imp_voted_off = meeting["outcome"] in impostors
                        vote_record[voter]["possible_points"] += hit_score
                        if len(vote) == 0:
                            vote_record[voter]["no_vote"] += 1
                        elif vote == "skip":
                            vote_record[voter]["skip"] += 1
                        elif vote in impostors:
                            vote_record[voter]["impostor"] += 1
                            vote_record[voter]["impostor_points"] += hit_score
                            if minority and not imp_voted_off:
                                vote_record[voter]["impostor_overruled"] += 1
                        else:
                            vote_record[voter]["crew"] += 1

        for player in vote_record.keys():
            vote_record[player]["skips"] = vote_record[player]["skip"] + vote_record[player]["no_vote"]
            vote_record[player]["non_skip"] = vote_record[player]["crew"] + vote_record[player]["impostor"]
            vote_record[player]["total"] = vote_record[player]["skips"] + vote_record[player]["non_skip"]

        characteristics = {
            player: {
                "boldness": round(100 * record["non_skip"] / record["total"]),
                "accuracy": round(100 * record["impostor"] / record["non_skip"]),
                "leader": round(100 * record["impostor_overruled"] / record["total"]),
                "detective": round(100 * record["impostor_points"] / record["possible_points"])
            }
            for player, record in vote_record.items()
        }
        characteristics = {key: characteristics[key] for key in sorted(characteristics.keys())}

        return vote_record, characteristics

    def get_impostor_pair_counts(self, win_only=False):
        i_pairs = defaultdict(dict)
        for date, rounds in self.combined_summaries.items():
            for r in rounds:
                if win_only and r.get("outcome", "unknown")[0] != "i":
                    continue
                impostors = r.get("impostors")
                if impostors is None:
                    continue
                if len(impostors) == 1:
                    impostors.append("solo")
                i_pairs[impostors[0]][impostors[1]] = i_pairs[impostors[0]].get(impostors[1], 0) + 1
                i_pairs[impostors[1]][impostors[0]] = i_pairs[impostors[0]][impostors[1]]
        return i_pairs

    def player_round_counts(self):
        play_counts = defaultdict(int)
        for date, rounds in self.combined_summaries.items():
            for round_info in rounds:
                round_players = round_info.get("player_list", [])
                for player in round_players:
                    play_counts[player] += 1
        players = sorted(play_counts.keys())
        play_counts = {player: play_counts[player] for player in players}
        return play_counts

    def killed_for_knowing_the_truth(self):
        case_counts = defaultdict(lambda: {"rounds": 0, "matches": 0})
        for date, rounds in self.combined_summaries.items():
            print(date)
            for round_info in rounds:
                # print("round")
                if "error" in round_info:
                    continue
                impostors = round_info["impostors"]
                crew = [player for player in round_info["player_list"] if player not in impostors]
                for player in crew:
                    case_counts[player]["rounds"] += 1
                if len(round_info["meetings"]) < 2:
                    continue
                prev_round_votes = round_info["meetings"][0]["vote_log"]
                prev_round_outcome = round_info["meetings"][0]["outcome"]
                for meeting in round_info["meetings"][1:]:
                    # print("meeting")
                    for player in meeting["new_dead"]:
                        if player not in crew:
                            continue
                        # if the player who died since last meeting voted for the impostor but impostor survived
                        if prev_round_votes[player] in impostors and prev_round_votes[player] != prev_round_outcome:
                            # if player == "Chris":
                            #     print("HERE")
                            case_counts[player]["matches"] += 1

        case_count_strings = {
            player: "{} / {} ({}%)".format(stats["matches"], stats["rounds"],
                                           round(stats["matches"] * 100 / stats["rounds"], 1))
            for player, stats in case_counts.items() if stats["matches"] > 0
        }
        ordered_players = sorted(case_count_strings.keys())
        case_count_strings = {player: case_count_strings[player] for player in ordered_players}
        return case_count_strings

    def first_to_die(self):
        case_counts = defaultdict(lambda: {"rounds": 0, "matches": 0})
        for date, rounds in self.combined_summaries.items():
            print(date)
            for round_info in rounds:
                # print("round")
                if "error" in round_info:
                    continue
                impostors = round_info["impostors"]
                crew = [player for player in round_info["player_list"] if player not in impostors]
                for player in crew:
                    case_counts[player]["rounds"] += 1
                for player in round_info["meetings"][0]["new_dead"]:
                    if player not in crew:
                        continue
                    case_counts[player]["matches"] += 1

        percs = {player: stats["matches"] * 100 / stats["rounds"] for player, stats in case_counts.items()}
        case_count_strings = {
            player: "{} / {} ({}%)".format(stats["matches"], stats["rounds"],
                                           round(stats["matches"] * 100 / stats["rounds"], 1))
            for player, stats in case_counts.items()
        }
        case_count_strings = {player: case_count_strings[player] for player in self.order_by_value(percs)}
        return case_count_strings

    def wrongly_ejected(self):
        case_counts = defaultdict(lambda: {"rounds": 0, "matches": 0})
        for date, rounds in self.combined_summaries.items():
            print(date)
            for round_info in rounds:
                # print("round")
                if "error" in round_info:
                    continue
                impostors = round_info["impostors"]
                crew = [player for player in round_info["player_list"] if player not in impostors]
                for player in crew:
                    case_counts[player]["rounds"] += 1
                for meeting in round_info["meetings"]:
                    if meeting["outcome"] in crew:
                        case_counts[meeting["outcome"]]["matches"] += 1

        percs = {player: stats["matches"] * 100 / stats["rounds"] for player, stats in case_counts.items()}
        case_count_strings = {
            player: "{} / {} ({}%)".format(stats["matches"], stats["rounds"],
                                           round(stats["matches"] * 100 / stats["rounds"], 1))
            for player, stats in case_counts.items()
        }
        case_count_strings = {player: case_count_strings[player] for player in self.order_by_value(percs)}
        return case_count_strings

    def colour_counts(self):
        case_counts = defaultdict(lambda: defaultdict(int))
        for date in self.combined_summaries.keys():
            print(date)
            for round_num in range(len(self.combined_summaries[date])):
                if "error" in self.combined_summaries[date][round_num]:
                    continue
                for player_num in range(len(self.combined_summaries[date][round_num]["player_list"])):
                    player_name = self.combined_summaries[date][round_num]["player_list"][player_num]
                    player_col = self.combined_summaries_colours[date][round_num]["player_list"][player_num]
                    case_counts[player_name][player_col] += 1

        case_counts = {player: case_counts[player] for player in sorted(case_counts.keys())}
        return case_counts

    def session_impostor_counts(self):
        case_counts = defaultdict(list)
        for date, rounds in self.combined_summaries.items():
            print(date)
            case_counts[date] = [{"players": round_info["player_list"],
                                  "impostors": round_info["impostors"]}
                                 for round_info in rounds if "error" not in round_info]

        return case_counts

    def breaking_the_law(self):
        # coming soon on Stats With Jesty
        pass

    @staticmethod
    def order_by_value(dictionary, field=None):
        if field is None:
            return dict(sorted(dictionary.items(), key=lambda item: item[1], reverse=True)).keys()
        else:
            return dict(sorted(dictionary.items(), key=lambda item: item[1][field], reverse=True)).keys()
