import os
import cv2
import json
import ffmpeg
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip


class AudioAnalyser:
    def __init__(self, date_str, game):
        self.date_str = date_str
        self.game = game
        self.video, self.video_path = self.get_video_stream(date_str, game)
        self.timestamps = self.get_video_timestamps(date_str, game)

    @staticmethod
    def get_video_stream(date_str, game, root=r"F:\Videos\Among Us"):
        video_path = os.path.join(root, date_str, "Among_Us_{} ({}).mp4".format(date_str, game))
        return ffmpeg.input(video_path), video_path

    @staticmethod
    def get_video_timestamps(date_str, game, root=r"F:\Videos\Among Us"):
        timestamps_path = os.path.join(root, date_str, "round_{}".format(game), "timestamps.json")
        with open(timestamps_path, "r") as f:
            timestamps = json.load(f)
        return timestamps

    def get_good_luck(self):
        snippet_end = self.timestamps["round_start"] / 1000
        snippet_end -= 5
        snippet_start = snippet_end - 10
        ffmpeg_extract_subclip(self.video_path, snippet_start, snippet_end, targetname="test.mp4")

if __name__ == '__main__':
    # aa = AudioAnalyser("May-06", 5)
    # # aa.get_good_luck()
    #
    # from moviepy.editor import VideoFileClip
    # full_vid = VideoFileClip(aa.video_path)
    # snippet_end = aa.timestamps["round_start"] / 1000
    # snippet_end -= 5
    # snippet_start = snippet_end - 10
    # snippet = full_vid.subclip(snippet_start, snippet_end)
    # audio = snippet.audio
    # audio.write_audiofile('audio_test.wav', ffmpeg_params=["-ac", "1"])

    import matplotlib.pyplot as plt
    from scipy import signal
    from scipy.io import wavfile
    import numpy as np

    sample_rate, samples = wavfile.read('audio_test.wav')
    frequencies, times, spectrogram = signal.spectrogram(samples, sample_rate)
    # get the average magnitude of frequencies during the "gooooood" and use it as a mask to find the pointwise distance between that and the frequency distribution at each timestamp
    # then define a threshold under which we consider the audio to be in the "goooood"
    # then select the longest segment of matches with a bit before & after
    plt.pcolormesh(times, frequencies, np.log(spectrogram))
    # plt.imshow(spectrogram)
    plt.ylabel('Frequency [Hz]')
    plt.xlabel('Time [sec]')
    plt.show()