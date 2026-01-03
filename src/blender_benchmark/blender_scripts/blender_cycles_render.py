#!/usr/bin/env python3
"""
Blender script for CYCLES rendering with custom samples setting.
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
    
    # Parse arguments: samples, output_path, and optional device
    if len(argv) >= 2:
        samples = int(argv[0])
        output_path = argv[1]
        device = None
        
        # Check for --cycles-device argument
        if "--cycles-device" in argv:
            device_idx = argv.index("--cycles-device")
            if device_idx + 1 < len(argv):
                device = argv[device_idx + 1]
    else:
        print("Error: Expected at least 2 arguments: samples and output_path")
        return
    
    # Set render engine to CYCLES
    bpy.context.scene.render.engine = 'CYCLES'
    
    # Set CYCLES samples
    bpy.context.scene.cycles.samples = samples
    print(f"Set Cycles samples to: {samples}")
    
    # Configure device if specified
    if device:
        print(f"Configuring Cycles device: {device}")
        if device == "CPU":
            bpy.context.scene.cycles.device = 'CPU'
        elif device in ["CUDA", "OPTIX", "OPENCL", "GPU"]:
            bpy.context.scene.cycles.device = 'GPU'
            # Try to set compute device type
            bpy.context.preferences.addons['cycles'].preferences.compute_device_type = device if device != "GPU" else "CUDA"
