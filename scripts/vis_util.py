import mechbayes.jhu as jhu
import os
from pathlib import Path
import json

'''Utilities for web visualization'''
def install_vis(prefix, places):

    print(f"Installing vis in {prefix}")

    here = Path(__file__).parent.resolve()

    # Copy index.html file
    src = f"{here}/resources/vis/index.html";
    dst = f"{prefix}/vis/index.html";
    os.system(f"cp {src} {dst}");

    # Write places.js file
    info = jhu.get_place_info();
    place2name = {place: info.loc[place, 'name'] for place in places}
    places_json = json.dumps(place2name);
    with open(f"{prefix}/vis/places.js", "w") as f:
        f.write(f'var places={places_json};')
