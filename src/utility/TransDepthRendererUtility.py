import csv
import os
from typing import List, Tuple, Union, Dict

import bpy
import mathutils
import numpy as np

from src.utility.BlenderUtility import load_image, get_all_blender_mesh_objects
from src.utility.MaterialLoaderUtility import MaterialLoaderUtility
from src.utility.RendererUtility import RendererUtility
from src.utility.WriterUtility import WriterUtility
from src.utility.Utility import Utility


class TransDepthRendererUtility:

    @staticmethod
    def _get_transmissiveness_output(material, threshold):
        """ Finds the transmissive component of a material and returns the node connection controlling it

        """

        # Steps:
        # - Find Node controlling transmission
        # - Return output (socket) that specifies if the material is transmissive
        print("getting output node of material: " + material.name);
        output_node = material.node_tree.get_output_node('CYCLES')
        surface_link = output_node.inputs['Surface'].links[0]

        shader_node = surface_link.from_node
        while True:
            if shader_node.type == 'REROUTE':
                # just follow the reroute
                shader_node = shader_node.inputs['Input'].links[0].from_node
                continue
            else:
                break

        if shader_node.type == 'BSDF_PRINCIPLED':
            transmission_input = shader_node.inputs['Transmission']

            if not transmission_input.is_linked:
                transmission_value = transmission_input.default_value
                value_node = material.node_tree.nodes.new('ShaderNodeValue')
                value_node.outputs['Value'].default_value = transmission_value
                value_node.location = (shader_node.location[0] - 300, shader_node.location[1])
                material.node_tree.links.new(value_node.outputs['Value'], transmission_input)

            gt_node = material.node_tree.nodes.new('ShaderNodeMath')
            gt_node.operation = 'GREATER_THAN'
            material.node_tree.links.new(transmission_input.links[0].from_socket, gt_node.inputs['Value'])
            # set threshold
            gt_node.inputs[1].default_value = threshold
            transmission_socket = gt_node.outputs['Value']
        else:
            if shader_node.type == 'BSDF_GLASS':
                # assume transmission to be 1 here
                transmission_value = 1
            elif shader_node.type == 'BSDF_REFRACTION':
                # assume transmission to be 1 here
                transmission_value = 1
            elif shader_node.type == 'BSDF_TRANSLUCENT':
                # Note: we might as well treat this one as opaque since it scatters so much
                transmission_value = 1
            else:
                # everything more complex (Mix Shader, OSL Nodes, ...) is not supported and is assumed to be opaque
                transmission_value = 0

            value_node = material.node_tree.nodes.new('ShaderNodeValue')
            value_node.outputs['Value'].default_value = transmission_value
            value_node.location = (shader_node.location[0] - 300, shader_node.location[1])
            transmission_socket = value_node.outputs['Value']

        # transmission socket is either 0 or 1 depending on if the material is transmissive or not
        return transmission_socket

    @staticmethod
    def _output_transmission_mask2(material, threshold: float, original_input, trans_out):
        """ Configures compositor to output transmission mask.

        Changes the materials to emissive if they are transparent, black (emissive) if they are opaque
        """
        bpy.context.scene.render.use_compositing = True
        bpy.context.scene.use_nodes = True

        # add an emission output for each material
        emission = material.node_tree.nodes.new('ShaderNodeEmission')
        material.node_tree.links.new(trans_out, emission.inputs['Strength'])

        material.node_tree.links.new(emission.outputs[0], original_input)

    # @staticmethod
    # def _output_normals_aov(material, aov_name, ignore_surface_output):
    #     """ Configures material shader to output normal information to custom AOV
    #
    #     """
    #
    #     not_node = material.node_tree.nodes.new('ShaderNodeMath')
    #     not_node.operation = "SUBTRACT"
    #     not_node.inputs[0].default_value = 1
    #     material.node_tree.links.new(ignore_surface_output, not_node.inputs[1])
    #
    #     mul_node = material.node_tree.nodes.new('ShaderNodeVectorMath')
    #     mul_node.operation = "MULTIPLY"
    #     material.node_tree.links.new(not_node.outputs[0], mul_node.inputs[0])
    #
    #     geo_node = material.node_tree.nodes.new('ShaderNodeNewGeometry')
    #     material.node_tree.links.new(geo_node.outputs["Normal"], mul_node.inputs[1])
    #
    #     aov_output = material.node_tree.nodes.new('ShaderNodeOutputAOV')
    #     aov_output.name = aov_name
    #     material.node_tree.links.new(mul_node.outputs[0], aov_output.inputs[0])

    # NOT USED ANYMORE
    @staticmethod
    def _output_transmission_mask(output_dir: str, file_name, output_key: str, threshold: float):
        """ Configures compositor to output transmission mask.

        :param output_dir: The directory to write images to.
        """

        bpy.context.scene.render.use_compositing = True
        bpy.context.scene.use_nodes = True

        # add transmask aov
        aov = bpy.data.scenes[0].view_layers[0].aovs.add()
        aov.name = "transmask"
        aov.type = "VALUE"

        # add a transparency output for each material
        for material in bpy.data.materials:
            trans_sock = TransDepthRendererUtility._get_transmissiveness_output(material, threshold)
            aov_output = material.node_tree.nodes.new('ShaderNodeOutputAOV')
            aov_output.name = aov.name

            material.node_tree.links.new(trans_sock, aov_output.inputs['Value'])

        # Edit compositor nodes
        tree = bpy.context.scene.node_tree
        links = tree.links

        # Use existing render layer
        render_layer_node = tree.nodes.get('Render Layers')

        output_file = tree.nodes.new('CompositorNodeOutputFile')
        output_file.base_path = output_dir
        output_file.format.file_format = "OPEN_EXR"
        output_file.file_slots.values()[0].path = file_name
        links.new(render_layer_node.outputs[aov.name], output_file.inputs['Image'])

        Utility.add_output_entry({
            "key": output_key,
            "path": os.path.join(output_dir, file_name) + "%04d" + ".exr",
            "version": "2.0.0"
        })

    @staticmethod
    def _transmission_to_transparency(material, depth, transmissiveness_output):
        """ Adds a node network which transforms surfaces to fully transparent one up to a given depth

        Essentially hides all surfaces that are transmissive that are not behind at least
        depth other transmissive surfaces
        """
        output_node = material.node_tree.get_output_node('CYCLES')
        links = material.node_tree.links

        original_shader = output_node.inputs['Surface'].links[0].from_socket

        # remove volume_link: volume rendering not supported for depth estimation
        if output_node.inputs['Volume'].is_linked:
            material.node_tree.links.remove(output_node.inputs['Volume'].links[0])

        light_path_node = material.node_tree.nodes.new('ShaderNodeLightPath')
        lt_node = material.node_tree.nodes.new('ShaderNodeMath')
        lt_node.operation = "LESS_THAN"
        and_node = material.node_tree.nodes.new('ShaderNodeMath')
        and_node.operation = "MULTIPLY"
        transparent_bsdf = material.node_tree.nodes.new('ShaderNodeBsdfTransparent')
        mix_node = material.node_tree.nodes.new('ShaderNodeMixShader')
        depth_control = material.node_tree.nodes.new('ShaderNodeValue')

        depth_control.outputs['Value'].default_value = depth
        links.new(depth_control.outputs[0], lt_node.inputs[1])
        links.new(light_path_node.outputs["Transparent Depth"], lt_node.inputs[0])

        links.new(lt_node.outputs[0], and_node.inputs[0])
        links.new(transmissiveness_output, and_node.inputs[1])

        links.new(and_node.outputs[0], mix_node.inputs['Fac'])
        links.new(transparent_bsdf.outputs[0], mix_node.inputs[2])
        links.new(original_shader, mix_node.inputs[1])

        links.new(mix_node.outputs[0], output_node.inputs['Surface'])

        # return mix shader as input for the original shader
        # and output that tells us if the surface should be ignored (outputs 1 for transparency)
        return mix_node.inputs[1], and_node.outputs[0]

    @staticmethod
    def _configure_scene(output_dir, threshold, depth):
        """

        """

        # add normal aov
        aov = bpy.data.scenes[0].view_layers[0].aovs.get("normalaov")
        if not aov:
            aov = bpy.data.scenes[0].view_layers[0].aovs.add()
            aov.name = "normalaov"
            aov.type = "COLOR"

        for material in bpy.data.materials:
            trans_out = TransDepthRendererUtility._get_transmissiveness_output(material, threshold)
            original_input, ignore_surface_output = TransDepthRendererUtility._transmission_to_transparency(material,
                                                                                                            depth,
                                                                                                            trans_out)

            # TransDepthRendererUtility._output_normals_aov(material, aov.name, ignore_surface_output)
            TransDepthRendererUtility._output_transmission_mask2(material, threshold, original_input, trans_out)

            # disable background
            world_out = bpy.context.scene.world.node_tree.get_output_node("CYCLES")
            surf = world_out.inputs['Surface']
            vol = world_out.inputs['Volume']
            if surf.is_linked:
                bpy.context.scene.world.node_tree.links.remove(surf.links[0])
            if vol.is_linked:
                bpy.context.scene.world.node_tree.links.remove(vol.links[0])

        # # Edit compositor output
        # tree = bpy.context.scene.node_tree
        # links = tree.links
        #
        # # Use existing render layer
        # render_layer_node = tree.nodes.get('Render Layers')
        #
        # file_prefix = "normals_" + str(depth) + "_"
        # output_file = tree.nodes.new('CompositorNodeOutputFile')
        # output_file.base_path = output_dir
        # output_file.format.file_format = "OPEN_EXR"
        # output_file.file_slots.values()[0].path = file_prefix
        # links.new(render_layer_node.outputs[aov.name], output_file.inputs['Image'])
        #
        # Utility.add_output_entry({
        #     "key": "normals_" + str(depth),
        #     "path": os.path.join(output_dir, file_prefix) + "%04d" + ".exr",
        #     "version": "2.0.0"
        # })

    @staticmethod
    def render(output_dir: str, temp_dir: str, depth_layers: int, transmission_steps: int, threshold: float):
        """

        """

        for depth in range(0, depth_layers * transmission_steps + 1, transmission_steps):
            with Utility.UndoAfterExecution(perform_undo_op=True):
                RendererUtility.init()
                RendererUtility.set_samples(1)
                RendererUtility.set_adaptive_sampling(0)
                RendererUtility.set_denoiser(None)
                RendererUtility.set_light_bounces(1, 0, 0, 1, 0, 8, 0)
                RendererUtility.set_output_format("OPEN_EXR", 16)

                TransDepthRendererUtility._configure_scene(output_dir, threshold, depth)

                distance_writer = RendererUtility.enable_distance_output(output_dir, "distance_" + str(depth) + "_",
                                                       "distance_" + str(depth))

                # Mask the distance output by our transparency mask
                # Reduces file size and cuts redundant information
                # tree = bpy.context.scene.node_tree
                # links = tree.links
                # mask_node = tree.nodes.new("CompositorNodeSetAlpha")
                # mask_node.mode = "APPLY"
                # links.new(tree.nodes.get('Render Layers').outputs["Image"], mask_node.inputs["Alpha"])
                # links.new(distance_writer.links[0].from_socket, mask_node.inputs["Image"])
                # links.new(mask_node.outputs[0], distance_writer)

                # make use of our custom aov
                tree = bpy.context.scene.node_tree
                norm_sock = Utility.get_the_one_node_with_type(tree.nodes, 'CompositorNodeRLayers').outputs["normalaov"]
                RendererUtility.enable_normals_output(output_dir, "normals_" + str(depth) + "_",
                                                      "normals_" + str(depth))
                RendererUtility.render(output_dir, "ntransmask_" + str(depth) + "_", "ntransmask_" + str(depth))
