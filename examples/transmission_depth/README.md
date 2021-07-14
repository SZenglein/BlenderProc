# Transmission Depth Pipeline

This configuration automatically creates a room using the random room constructor 
using the provided .blend files for populating the room. 
It then adds some objects for transparency training from a set of .blend files
and randomly manipulates these objects by setting different materials or 
geometry modifiers.

## Usage

```
python run.py transmission_depth/config.yaml path/to/furniture/blends path/to/cc_materials path/to/transmissive_objects /path/to/output_dir
```

## Visualization
Visualize the generated data:

```
python scripts/visHdf5Files.py output_dir/0.hdf5
```

## Steps

* Constructs a random room using cc_textures and provided .blend objects (see random room constructor example)
* Adds some objects with random properties (e.g. transmissive)
* Applies physics to let added objects fall down
* Samples camera positions based on "interestingness"
* Renders rgb, normals and distance for multiple depth levels
* Writes the output to .hdf5 containers: `writer.Hdf5Writer` module.

