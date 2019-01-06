import json
from io import BytesIO
from random import randint

import h5py
import numpy as np
from scipy import misc
from torch.utils.data import Dataset
from tqdm import tqdm, trange


class VideoDataset(Dataset):
    def __init__(self, annotation_file, database_file, num_frames_per_clip=0, crop_size=0):
        self.num_frames_per_clip = num_frames_per_clip
        assert self.num_frames_per_clip >= 0
        self.crop_size = crop_size
        assert self.crop_size >= 0

        self.annotation = json.load(open(annotation_file, "r"))
        self.database = h5py.File(database_file, 'r')
        self.len = len(self.annotation)

    def __getitem__(self, index):
        annotation = self.annotation[index]

        # Get the binary frames
        frames_binary = self.database["{:08d}".format(index)]

        # Sample the frames
        if self.num_frames_per_clip:
            if self.num_frames_per_clip == 1:
                frame_index = [len(frames_binary) / 2]
            else:
                skips = (len(frames_binary) - 1) * 1. / (self.num_frames_per_clip - 1)
                frame_index = [round(x * skips) for x in range(self.num_frames_per_clip)]
        else:
            frame_index = list(range(len(frames_binary)))

        # Decode the frames
        video_data = [
            misc.imread(
                BytesIO(
                    np.asarray(
                        frames_binary["{:08d}".format(idx)]
                    ).tostring()
                )
            ) for idx in frame_index
        ]
        video_data = np.array(video_data)

        # Crop the videos
        if self.crop_size:
            _, h, w, _ = video_data.shape
            y1 = randint(0, h - self.crop_size - 1)
            x1 = randint(0, w - self.crop_size - 1)
            y2, x2 = y1 + self.crop_size, x1 + self.crop_size
            video_data = video_data[:, y1:y2, x1:x2, :]

        return video_data, annotation['class']

    def __len__(self):
        return self.len

    def __repr__(self):
        return "{} {} videos, {}, {}".format(
            type(self), len(self),
            "Sample to {} frames".format(self.num_frames_per_clip) if self.num_frames_per_clip else "Not sampled",
            "Crop to {}".format(self.crop_size) if self.crop_size else "Not cropped")


if "__main__" == __name__:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("annotation", type=str, help="The annotation file, in json format")
    parser.add_argument("data", type=str, help="The hdf5 file")
    parser.add_argument("--frames", type=int, default=16, help="Num of frames per clip")
    parser.add_argument("--crop", type=int, default=160, help="Crop size")
    args = parser.parse_args()

    dataset = VideoDataset(args.annotation, args.data, args.frames, args.crop)
    error_index = []
    for x in trange(len(dataset)):
        try:
            frame, label = dataset[x]
            tqdm.write("Index {}, Class Label {}, Shape {}".format(x, label, frame.shape))
        except Exception as e:
            tqdm.write("=====> Video {} check failed".format(x))
            error_index.append(x)

    if not error_index:
        print("All is well! Congratulations!")
    else:
        print("Ooops! There are {} bad videos:".format(len(error_index)))
        print(error_index)
