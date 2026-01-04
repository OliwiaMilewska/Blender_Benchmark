#!/usr/bin/env python3
"""
Blender script for EEVEE rendering with custom samples setting.
This script is meant to be executed within Blender using --python parameter.
"""
import bpy
import sys

def main():
    # Get command line arguments passed to Blender
    # Arguments after -- are available in sys.argv
    argv = sys.argv
    
    # Find arguments after "--"
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    
    # Parse arguments: samples, output_path
    if len(argv) >= 2:
        samples = int(argv[0])
        output_path = argv[1]
    else:
        print("Error: Expected at least 2 arguments: samples and output_path")
        return
    
    # Set render engine to EEVEE
    bpy.context.scene.render.engine = 'BLENDER_EEVEE'
    
    # Set EEVEE samples
    bpy.context.scene.eevee.taa_render_samples = samples
    print(f"Set EEVEE samples to: {samples}")
    
    # Set output path and format
    bpy.context.scene.render.filepath = output_path
    bpy.context.scene.render.image_settings.file_format = 'PNG'
    
    # Render
    print(f"Starting render with {samples} samples...")
    bpy.ops.render.render(write_still=True)
    
    print(f"EEVEE render completed with {samples} samples, saved to: {output_path}")

if __name__ == "__main__":
    main()
