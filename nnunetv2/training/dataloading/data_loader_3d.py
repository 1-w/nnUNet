import numpy as np
import torch
from threadpoolctl import threadpool_limits

from nnunetv2.training.dataloading.base_data_loader import nnUNetDataLoaderBase
from nnunetv2.training.dataloading.nnunet_dataset import nnUNetDataset
from typing import Union, Tuple
from batchgenerators.utilities.file_and_folder_operations import *
from nnunetv2.utilities.label_handling.label_handling import LabelManager


class nnUNetDataLoader3D(nnUNetDataLoaderBase):
    def generate_train_batch(self):
        selected_keys = self.get_indices()
        # preallocate memory for data and seg
        data_all = np.zeros(self.data_shape, dtype=np.float32)
        seg_all = np.zeros(self.seg_shape, dtype=np.int16)
        case_properties = []

        for j, i in enumerate(selected_keys):
            # oversampling foreground will improve stability of model training, especially if many patches are empty
            # (Lung for example)
            force_fg = self.get_do_oversample(j)

            data, seg, properties = self._data.load_case(i)
            case_properties.append(properties)

            # If we are doing the cascade then the segmentation from the previous stage will already have been loaded by
            # self._data.load_case(i) (see nnUNetDataset.load_case)
            shape = data.shape[1:]
            dim = len(shape)
            bbox_lbs, bbox_ubs = self.get_bbox(
                shape, force_fg, properties["class_locations"]
            )

            # whoever wrote this knew what he was doing (hint: it was me). We first crop the data to the region of the
            # bbox that actually lies within the data. This will result in a smaller array which is then faster to pad.
            # valid_bbox is just the coord that lied within the data cube. It will be padded to match the patch size
            # later
            valid_bbox_lbs = [max(0, bbox_lbs[i]) for i in range(dim)]
            valid_bbox_ubs = [min(shape[i], bbox_ubs[i]) for i in range(dim)]

            # At this point you might ask yourself why we would treat seg differently from seg_from_previous_stage.
            # Why not just concatenate them here and forget about the if statements? Well that's because segneeds to
            # be padded with -1 constant whereas seg_from_previous_stage needs to be padded with 0s (we could also
            # remove label -1 in the data augmentation but this way it is less error prone)
            this_slice = tuple(
                [slice(0, data.shape[0])]
                + [slice(i, j) for i, j in zip(valid_bbox_lbs, valid_bbox_ubs)]
            )
            data = data[this_slice]

            this_slice = tuple(
                [slice(0, seg.shape[0])]
                + [slice(i, j) for i, j in zip(valid_bbox_lbs, valid_bbox_ubs)]
            )
            seg = seg[this_slice]

            padding = [
                (-min(0, bbox_lbs[i]), max(bbox_ubs[i] - shape[i], 0))
                for i in range(dim)
            ]
            data_all[j] = np.pad(
                data, ((0, 0), *padding), "constant", constant_values=0
            )
            seg_all[j] = np.pad(seg, ((0, 0), *padding), "constant", constant_values=-1)

        return {
            "data": data_all,
            "seg": seg_all,
            "properties": case_properties,
            "keys": selected_keys,
        }


class nnUNetThreewayDataLoader3D(nnUNetDataLoaderBase):

    def determine_shapes(self):
        # load one case
        data, seg, seg2, properties = self._data.load_case(self.indices[0])
        num_color_channels = data.shape[0]

        data_shape = (self.batch_size, num_color_channels, *self.patch_size)
        seg_shape = (self.batch_size, seg.shape[0], *self.patch_size)
        seg2_shape = (self.batch_size, seg2.shape[0], *self.patch_size)
        return data_shape, seg_shape

    def generate_train_batch(self):
        selected_keys = self.get_indices()
        # preallocate memory for data and seg
        data_all = np.zeros(self.data_shape, dtype=np.float32)
        seg_all = np.zeros(self.seg_shape, dtype=np.int16)
        seg2_all = np.zeros(self.seg_shape, dtype=np.int16)
        case_properties = []

        for j, i in enumerate(selected_keys):
            # oversampling foreground will improve stability of model training, especially if many patches are empty
            # (Lung for example)
            force_fg = self.get_do_oversample(j)

            data, seg, seg2, properties = self._data.load_case(i)
            case_properties.append(properties)

            # If we are doing the cascade then the segmentation from the previous stage will already have been loaded by
            # self._data.load_case(i) (see nnUNetDataset.load_case)
            shape = data.shape[1:]
            dim = len(shape)
            bbox_lbs, bbox_ubs = self.get_bbox(
                shape, force_fg, properties["class_locations"]
            )

            # whoever wrote this knew what he was doing (hint: it was me). We first crop the data to the region of the
            # bbox that actually lies within the data. This will result in a smaller array which is then faster to pad.
            # valid_bbox is just the coord that lied within the data cube. It will be padded to match the patch size
            # later
            valid_bbox_lbs = np.clip(bbox_lbs, a_min=0, a_max=None)
            valid_bbox_ubs = np.minimum(shape, bbox_ubs)

            # At this point you might ask yourself why we would treat seg differently from seg_from_previous_stage.
            # Why not just concatenate them here and forget about the if statements? Well that's because segneeds to
            # be padded with -1 constant whereas seg_from_previous_stage needs to be padded with 0s (we could also
            # remove label -1 in the data augmentation but this way it is less error prone)
            this_slice = tuple(
                [slice(0, data.shape[0])]
                + [slice(i, j) for i, j in zip(valid_bbox_lbs, valid_bbox_ubs)]
            )
            data = data[this_slice]

            this_slice = tuple(
                [slice(0, seg.shape[0])]
                + [slice(i, j) for i, j in zip(valid_bbox_lbs, valid_bbox_ubs)]
            )
            seg = seg[this_slice]

            this_slice = tuple(
                [slice(0, seg2.shape[0])]
                + [slice(i, j) for i, j in zip(valid_bbox_lbs, valid_bbox_ubs)]
            )
            seg2 = seg2[this_slice]

            padding = [
                (-min(0, bbox_lbs[i]), max(bbox_ubs[i] - shape[i], 0))
                for i in range(dim)
            ]
            data_all[j] = np.pad(
                data, ((0, 0), *padding), "constant", constant_values=0
            )
            seg_all[j] = np.pad(seg, ((0, 0), *padding), "constant", constant_values=-1)
            seg2_all[j] = np.pad(
                seg2, ((0, 0), *padding), "constant", constant_values=-1
            )

        return {
            "data": data_all,
            "seg": seg_all,
            "seg2": seg2_all,
            "properties": case_properties,
            "keys": selected_keys,
        }


if __name__ == "__main__":
    folder = "/media/fabian/data/nnUNet_preprocessed/Dataset002_Heart/3d_fullres"
    ds = nnUNetDataset(folder, 0)  # this should not load the properties!
    dl = nnUNetDataLoader3D(ds, 5, (16, 16, 16), (16, 16, 16), 0.33, None, None)
    a = next(dl)
