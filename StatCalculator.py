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

    def impostor_ratio_win_rates(self):
        case_counts = defaultdict(lambda: {"impostor_kill": 0, "crew_tasks": 0, "crew_vote": 0, "impostor_vote": 0})
        for date, rounds in self.combined_summaries.items():
            for round_info in rounds:
                if "error" in round_info:
                    continue
                impostor_count = len(round_info["impostors"])
                crew_count = len(round_info["player_list"]) - impostor_count
                case_counts["{}:{}".format(impostor_count, crew_count)][round_info["outcome"]] += 1
        return case_counts

    def breaking_the_law(self):
        # coming soon on Stats With Jesty
        pass

    def voting_on_x(self, total_alive=7, impostors_alive=2):
        case_counts = defaultdict(lambda: {"correct": 0, "incorrect": 0, "total": 0, "opportunities": 0})
        for date, games in self.combined_summaries.items():
            for game in games:
                if "error" in game:
                    continue
                impostors = game["impostors"]
                for meeting in game["meetings"]:
                    if total_alive != len(meeting["alive"]):
                        continue
                    if impostors_alive is not None and \
                            impostors_alive != len([player for player in impostors if player in meeting["alive"]]):
                        continue
                    for player, vote in meeting["vote_log"].items():
                        if player not in impostors:
                            continue
                        case_counts[player]["opportunities"] += 1
                        if vote not in ["skip", ""]:
                            case_counts[player]["total"] += 1
                            if vote in impostors:
                                case_counts[player]["correct"] += 1
                            else:
                                case_counts[player]["incorrect"] += 1
        percentages = {
            player: {
                **stats,
                "perc_votes_cast": round(100 * stats["total"] / stats["opportunities"]),
                "perc_votes_correct": round(100 * stats["correct"] / stats["total"])
            }
            for player, stats in case_counts.items() if stats["total"] > 0
        }
        percentages = self.order_by_value(percentages, field="perc_votes_cast", keys_only=False)
        title = "In meetings with {} players alive".format(total_alive)
        if impostors_alive is not None:
            title += " {} of whom were impostors".format(impostors_alive)
        print(title + ":")
        out_string = "{} voted in {}/{} of meetings ({}%), with {} correct votes ({}%)"
        for player, stats in percentages.items():
            print(out_string.format(
                player, stats["total"], stats["opportunities"], stats["perc_votes_cast"], stats["correct"],
                stats["perc_votes_correct"]
            ))
            out_string = "{}          {}/{}             ({}%),      {}               ({}%)"
        return case_counts, percentages

    def search_for_round(self, category, data=None):
        for date, games in self.combined_summaries.items():
            game_num = 0
            for game in games:
                game_num += 1
                if "error" in game:
                    continue
                round_str = "{} round {}".format(date, game_num)
                if category == "impostor":
                    impostors = data
                    impostor_match = True
                    for player in impostors:
                        if player not in game["impostors"]:
                            impostor_match = False
                    if impostor_match:
                        print(round_str)
                elif category == "half_impostor_win":
                    if len(game["impostors"]) != 2 or game["outcome"][0] != "i":
                        continue
                    final_meeting = game["meetings"][-1]
                    impostors_survived = [player for player in game["impostors"]
                                          if player in final_meeting["alive"] and player != final_meeting["outcome"]]
                    if len(impostors_survived) == 1:
                        round_str += " impostors {}, {} survived".format(str(game["impostors"]), impostors_survived[0])
                        print(round_str)

    def best_at_dying(self):
        case_counts = defaultdict(lambda: {"opportunity": 0.0, "score": 0.0})
        for date, games in self.combined_summaries.items():
            for game in games:
                if "error" in game:
                    continue
                for meeting in game["meetings"]:
                    score_round = meeting["outcome"] in game["impostors"]
                    value = 1 / len(meeting["new_dead"]) if len(meeting["new_dead"]) > 0 else 0.0
                    for player in meeting["new_dead"]:
                        case_counts[player]["opportunity"] += value
                        if score_round:
                            case_counts[player]["score"] += value
        percs = {
            player: round(100 * stats["score"] / stats["opportunity"])
            for player, stats in case_counts.items()
        }
        return self.order_by_value(percs, keys_only=False)

    def impostor_kills_per_round(self):
        case_counts = defaultdict(lambda: {"kills": 0.0, "rounds": 0})
        for date, games in self.combined_summaries.items():
            for game in games:
                if "error" in game or len(game["impostors"]) != 2:
                    continue
                for impostor in game["impostors"]:
                    case_counts[impostor]["rounds"] += 1
                for meeting in game["meetings"]:
                    impostors_alive = [player for player in game["impostors"] if player in meeting["alive"]]
                    for impostor in impostors_alive:
                        case_counts[impostor]["kills"] += (len(meeting["new_dead"]) / len(impostors_alive))
        percs = {
            player: round(stats["kills"] / stats["rounds"], 2)
            for player, stats in case_counts.items() if stats["rounds"] > 0
        }
        return self.order_by_value(percs, keys_only=False)

    def game_lengths(self):
        lengths_by_outcome = defaultdict(lambda: {"total_time": 0, "round_count": 0, "longest": 0, "shortest": 9999999})
        longest_game = {"date": "Apr-03", "round_num": 1, "length": 0}
        shortest_game = {"date": "Apr-03", "round_num": 1, "length": 100000}
        total_length = 0
        number_of_rounds = 0
        for date, games in self.combined_summaries.items():
            for game_num in range(len(games)):
                game = games[game_num]
                if "error" in game or len(game["impostors"]) != 2:
                    continue
                number_of_rounds += 1
                game_len = self.time_to_seconds(game["round_length"])
                total_length += game_len
                if game_len > longest_game["length"]:
                    longest_game = {"date": date, "round_num": game_num + 1, "length": game_len}
                if game_len < shortest_game["length"]:
                    shortest_game = {"date": date, "round_num": game_num + 1, "length": game_len}
                lengths_by_outcome[game["outcome"]]["round_count"] += 1
                lengths_by_outcome[game["outcome"]]["total_time"] += game_len
                if game_len > lengths_by_outcome[game["outcome"]]["longest"]:
                    lengths_by_outcome[game["outcome"]]["longest"] = game_len
                if game_len < lengths_by_outcome[game["outcome"]]["shortest"]:
                    lengths_by_outcome[game["outcome"]]["shortest"] = game_len
        print("Total recorded playtime: {}".format(self.seconds_to_time(total_length)))
        print("Average game length: {}".format(self.seconds_to_time(total_length / number_of_rounds)))
        print("Longest game: {} (round {} on {})".format(self.seconds_to_time(longest_game["length"]),
                                                         longest_game["round_num"], longest_game["date"]))
        print("Shortest game: {} (round {} on {})".format(self.seconds_to_time(shortest_game["length"]),
                                                          shortest_game["round_num"], shortest_game["date"]))
        lengths_by_outcome = {
            outcome: {
                "rounds": stats["round_count"],
                "total_time": self.seconds_to_time(stats["total_time"]),
                "shortest": self.seconds_to_time(stats["shortest"]),
                "average": self.seconds_to_time(stats["total_time"] / stats["round_count"]),
                "longest": self.seconds_to_time(stats["longest"])
            } for outcome, stats in lengths_by_outcome.items()
        }
        print(json.dumps(lengths_by_outcome, indent=4))

    def game_lengths_by_impostor(self):
        case_counts = defaultdict(lambda: defaultdict(lambda: {"total_time": 0, "round_count": 0, "alive_time": 0}))
        for date, games in self.combined_summaries.items():
            for game in games:
                if "error" in game or len(game["impostors"]) != 2:
                    continue
                impostor_win = "win" if game["outcome"][0] == "i" else "loss"
                game_start_secs = self.time_to_seconds(game["round_start"])
                for meeting in game["meetings"]:
                    if meeting["outcome"] in game["impostors"]:
                        game_length_so_far = self.time_to_seconds(meeting["end"]) - game_start_secs
                        case_counts[meeting["outcome"]][impostor_win]["alive_time"] += game_length_so_far
                game_len = self.time_to_seconds(game["round_length"])
                for impostor in game["impostors"]:
                    case_counts[impostor][impostor_win]["total_time"] += game_len
                    case_counts[impostor][impostor_win]["round_count"] += 1
                    if impostor in game["meetings"][-1]["alive"] and impostor != game["meetings"][-1]["outcome"]:
                        case_counts[impostor][impostor_win]["alive_time"] += game_len
        percs = defaultdict(dict)
        for player, stats in case_counts.items():
            for outcome in ["win", "loss"]:
                num_rounds = stats[outcome]["round_count"]
                if num_rounds > 0:
                    avg_time = self.seconds_to_time(stats[outcome]["total_time"] / num_rounds)
                    avg_alive_time = self.seconds_to_time(stats[outcome]["alive_time"] / num_rounds)
                    percs[player][outcome] = "{} ({})".format(avg_time, avg_alive_time)
            num_rounds = stats["win"]["round_count"] + stats["loss"]["round_count"]
            avg_time = self.seconds_to_time((stats["win"]["total_time"] + stats["loss"]["total_time"]) / num_rounds)
            avg_alive_time = self.seconds_to_time(
                (stats["win"]["alive_time"] + stats["loss"]["alive_time"]) / num_rounds)
            percs[player]["overall"] = "{} ({})".format(avg_time, avg_alive_time)
        print(json.dumps(percs, indent=4))

    def game_lengths_by_crew(self):
        case_counts = defaultdict(lambda: {"round_count": 0, "alive_time": 0})
        total_time = 0
        total_meeting_time = 0
        round_count = 0
        for date, games in self.combined_summaries.items():
            for game in games:
                if "error" in game or len(game["impostors"]) != 2:
                    continue
                total_time += self.time_to_seconds(game["round_length"])
                round_count += 1
                crew = [player for player in game["player_list"] if player not in game["impostors"]]
                non_meeting_time = 0
                for meeting_num in range(len(game["meetings"])):
                    meeting = game["meetings"][meeting_num]
                    total_meeting_time += self.time_to_seconds(meeting["meeting_length"])
                    cooldown = 15 if meeting_num == 0 else 30
                    play_length = self.time_to_seconds(meeting["play_length"]) - cooldown
                    non_meeting_time += cooldown + (play_length / 2)
                    new_dead = meeting["new_dead"]
                    new_dead.append(meeting["outcome"])
                    for player in new_dead:
                        if player in crew:
                            case_counts[player]["round_count"] += 1
                            case_counts[player]["alive_time"] += non_meeting_time
                    non_meeting_time += (play_length / 2)
                # meeting variable is now final meeting
                final_session_length = self.time_to_seconds(game["round_end"]) - self.time_to_seconds(meeting["end"])
                live_crew_end = [player for player in meeting["alive"]
                                 if player in crew and player != meeting["outcome"]]
                for player in live_crew_end:
                    case_counts[player]["round_count"] += 1
                    case_counts[player]["alive_time"] += non_meeting_time + final_session_length
        averages = {
            player: self.seconds_to_time(stats["alive_time"] / stats["round_count"])
            for player, stats in case_counts.items()
        }
        print("Average round time: {} with {} spent in meetings and {} running / floating around".format(
            self.seconds_to_time(total_time / round_count),
            self.seconds_to_time(total_meeting_time / round_count),
            self.seconds_to_time((total_time - total_meeting_time) / round_count)
        ))
        print(json.dumps(self.order_by_value(averages, keys_only=False), indent=4))

    @staticmethod
    def order_by_value(dictionary, field=None, keys_only=True):
        if field is None:
            sorted_dict = dict(sorted(dictionary.items(), key=lambda item: item[1], reverse=True))
        else:
            sorted_dict = dict(sorted(dictionary.items(), key=lambda item: item[1][field], reverse=True))
        if keys_only:
            return sorted_dict.keys()
        else:
            return sorted_dict

    @staticmethod
    def time_to_seconds(time):
        mins, secs = time.split(":")
        return (int(mins) * 60) + int(secs)

    @staticmethod
    def seconds_to_time(full_secs):
        time = full_secs
        secs = int(time % 60)
        time = (time - secs) / 60
        mins = int(time % 60)
        hours = int((time - mins) / 60)
        if hours > 0:
            components = [hours, mins, secs]
        else:
            components = [mins, secs]
        return ":".join(["{:02d}".format(num) for num in components])


if __name__ == '__main__':
    print(StatCalculator.seconds_to_time(3600))
