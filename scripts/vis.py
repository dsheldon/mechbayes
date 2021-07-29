import mechbayes.jhu as jhu
import os
from pathlib import Path

'''Utilities for web visualization'''
def install_vis(prefix, places):
    print(f"Installing vis in {prefix}")

    here = Path(__file__).parent.resolve()
    
    # Copy index.html file
    src = f"{here}/vis/index.html";
    dst = f"{prefix}/vis/index.html";
    os.system(f"cp {src} {dst}");

    # Write places.js file
    info = jhu.get_place_info();
    json = info[info.index.isin(places)]['name'].to_json(orient='index')
    with open(f"{prefix}/vis/places.js", "w") as f:
        f.write(f'var places={json};')

