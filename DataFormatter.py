def summarise_data(round_start, round_end, meetings):
    output = {
        "version": None,
        "round_start": format_ms(round_start),
        "round_end": format_ms(round_end),
        "round_length": format_ms(round_end - round_start),
        "impostors": None,
        "player_list": [],
        "outcome": None,
        "meetings": []
    }
    prev_end = round_start
    prev_dead = set([])
    meeting_num = 0
    for meeting in meetings:
        meeting_num += 1
        screenshot_data = meeting["screenshot_summary"]
        if meeting_num == 1:
            output["player_list"] = [row["colour"] for row in screenshot_data["rows"]]
        meeting_details = {
            "play_length": format_ms(meeting["start"] - prev_end),
            "start": format_ms(meeting["start"]),
            "end": format_ms(meeting["end"]),
            "meeting_length": format_ms(meeting["end"] - meeting["start"]),
            "reporter": [row["colour"] for row in screenshot_data["rows"] if row["reporter"]][0],
            "alive": [row["colour"] for row in screenshot_data["rows"] if row["alive"]],
            "dead": [row["colour"] for row in screenshot_data["rows"] if not row["alive"]],
            "new_dead": list(set([row["colour"] for row in screenshot_data["rows"] if not row["alive"]]) - prev_dead),
            "vote_log": {},
            "votes_for": {},
            "outcome": ""
        }
        # vote counts
        votes_for = {row["colour"]: len(row["votes_for"]) for row in screenshot_data["rows"] if
                     len(row["votes_for"]) > 0}
        votes_for["skip"] = len(screenshot_data["skips"])
        meeting_details["votes_for"] = dict(sorted(votes_for.items(), key=lambda item: item[1], reverse=True))

        # vote log
        vote_log = {player: "" for player in meeting_details["alive"]}
        for row in screenshot_data["rows"]:
            for voter in row["votes_for"]:
                vote_log[voter] = row["colour"]
        for voter in screenshot_data["skips"]:
            vote_log[voter] = "skip"
        meeting_details["vote_log"] = vote_log

        # outcome
        vote_nums = sorted(votes_for.values(), reverse=True)
        if len(vote_nums) > 1 and vote_nums[0] == vote_nums[1]:
            meeting_details["outcome"] = "tied"
        else:
            keys = meeting_details["votes_for"].keys()
            meeting_details["outcome"] = list(meeting_details["votes_for"])[0]

        # append to main structure
        output["meetings"].append(meeting_details)

        # log for next iter
        prev_dead = set(meeting_details["dead"] + [meeting_details["outcome"]])
        prev_end = meeting["end"]

    return output


def format_ms(ms_time):
    ds = int((ms_time / 100.0) % 10)
    sec = int((ms_time / 1000.0) % 60)
    min = int((ms_time / 60000.0) % 60)
    return "{:02d}:{:02d}".format(min, sec, ds)
