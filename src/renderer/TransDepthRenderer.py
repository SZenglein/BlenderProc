import csv
import os

import bpy
import numpy as np

from src.renderer.RendererInterface import RendererInterface
from src.utility.BlenderUtility import load_image, get_all_blender_mesh_objects
from src.utility.TransDepthRendererUtility import TransDepthRendererUtility
from src.utility.Utility import Utility


class TransDepthRenderer(RendererInterface):

    def __init__(self, config):
        RendererInterface.__init__(self, config)

    def run(self):
        with Utility.UndoAfterExecution(perform_undo_op=True):
            self._configure_renderer()

            # get the number of depth layers that should be rendered
            depth_layers = self.config.get_int("depth_layers", 6)
            # get the number of transmission bounces between layers (e.g. 2 to not render backside depth)
            transmission_steps = self.config.get_int("transmission_steps", 1)

            if not self._avoid_output:
                TransDepthRendererUtility.render(
                    self._determine_output_dir(),
                    self._temp_dir,
                    depth_layers,
                    transmission_steps,
                    threshold=0.1,
                )

        # with Utility.UndoAfterExecution():
        #     self._configure_renderer(default_samples=1)
        #
        #     if not self._avoid_rendering:
        #         TransDepthRendererUtility.render(
        #
        #         )
        #
        #
        #
        #
        #         SegMapRendererUtility.render(
        #             self._determine_output_dir(),
        #             self._temp_dir,
        #             used_attributes,
        #             used_default_values,
        #             self.config.get_string("output_file_prefix", "segmap_"),
        #             self.config.get_string("output_key", "segmap"),
        #             self.config.get_string("segcolormap_output_file_prefix", "class_inst_col_map"),
        #             self.config.get_string("segcolormap_output_key", "segcolormap"),
        #             use_alpha_channel=self._use_alpha_channel
        #         )
