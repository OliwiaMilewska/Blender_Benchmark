#!/usr/bin/env python3
import bpy
import sys

def main():
    argv = sys.argv

    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    if len(argv) >= 2:
        try:
            samples = int(argv[0]) if argv[0] != "None" else 64
        except ValueError:
            print(f"Invalid samples '{argv[0]}', using default 64")
            samples = 64

        output_path = argv[1]

        # Domyślny profil = MEDIUM
        profile = "MEDIUM"

        i = 2
        while i < len(argv):
            if argv[i] == "--profile" and i + 1 < len(argv):
                profile = argv[i + 1].upper()
                i += 2
            else:
                i += 1
    else:
        print("Error: Expected at least 2 arguments: samples and output_path")
        return

    scene = bpy.context.scene

    # --- ENGINE ---
    scene.render.engine = 'BLENDER_EEVEE'

    # --- SAMPLES ---
    scene.eevee.taa_render_samples = samples
    print(f"Samples: {samples}")

    # --- PROFILE SETTINGS ---
    print(f"Using profile: {profile}")

    if profile == "LOW":
        scene.eevee.shadow_pool_size = '512'
        scene.eevee.taa_render_samples = 4

    elif profile == "MEDIUM":
        scene.eevee.shadow_pool_size = '1024'
        scene.eevee.taa_render_samples = 8

    else:  # HIGH
        scene.eevee.shadow_pool_size = '2048'
        scene.eevee.taa_render_samples = 16

    # --- OUTPUT ---
    scene.render.filepath = output_path
    scene.render.image_settings.file_format = 'PNG'

    # --- RENDER ---
    print("Starting render...")
    bpy.ops.render.render(write_still=True)

    print(f"EEVEE render completed, saved to: {output_path}")
    
if __name__ == "__main__":
    main()