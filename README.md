# sky-archipelago

In this repository, I attempted to procedurally generate floating islands. Using panda3D’s GeoMipTerrain, I created two terrain meshes from heightmap images. I then overlaid the two islands, with one flipped upside down. For educational purposes, I also wrote code to create the same floating islands using ShaderTerrainMesh. The buildings and vegetation on the islands were generated using the same method as in  [VoronoiCity3](https://github.com/taKana671/VoronoiCity3.git),. The sea of clouds was rendered by applying a shader to a flat 3D object.

<img width="795" height="622" alt="Image" src="https://github.com/user-attachments/assets/937aa374-21c9-48fb-86b4-cf69b2933428" />

# Future Challenges

Despite repeated trial and error, I was unable to align the top and bottom terrain layers perfectly without any gaps. Additionally, the edges ended up jagged, which doesn’t look very nice when viewed up close.
I’d like to find a way to eliminate these gaps and achieve a clean finish along the edges.
If anyone knows how to do this, I’d greatly appreciate your help.

<img width="779" height="257" alt="Image" src="https://github.com/user-attachments/assets/1ec07962-264c-4038-a0c2-96947e9adcde" />


# Requirements

* Panda3D 1.10.16
* Cython 3.2.3
* numpy 2.2.6
* scipy 1.16.2
* shapely 2.1.2
* matplotlib 3.10.7
* opencv-contrib-python 4.11.0.86
* opencv-python 4.11.0.86
* PyYAML 6.0.3

# Environment

* Python 3.13
* Windows11

# Usage

### Clone this repository.

```
git clone --recursive https://github.com/taKana671/sky-archipelago.git sky_archipelago
```

### Build cython code.

If you do not build the Cython code, Python code will be used to generate noise. <br>
Python code takes longer to generate noise than Cython code.

```
cd sky_archipelago
python setup.py build_ext --inplace
```

If the error like "ModuleNotFoundError: No module named ‘distutils’" occurs, install the setuptools.

```
pip install setuptools
```

### Run sky_archipelago.py

```
python sky_archipelago.py
```

* By changing the settings in ```sky_archipelago_config.yaml```, you can switch modes as shown below.

<table>
    <tr>
      <th>key</th>
      <th>value</th>
      <th>description</th>
    </tr>
    <tr>
      <th>mode</th>
      <th>1</th>
      <th align="left">Fixed camera position</th>
    </tr>
    <tr>
      <th></th>
      <th>2</th>
      <th align="left">You can change the camera's position and orientation using the keyboard.</th>
    </tr>
    <tr>
      <th></th>
      <th>3</th>
      <th align="left">You can rotate the islands by dragging with the mouse.</th>
    </tr>
    <tr>
      <th>do_positioning</th>
      <th>true</th>
      <th align="left">Setting to true allows you to position 3D objects using keyboard. Since it was difficult to adjust the positions of each island, the camera position, and the camera’s viewpoint, this feature was created to facilitate positioning. You can switch between positioning targets using the [n] key. For details, please refer to the code in sky_archipelago.py.</th>
    </tr>
</table>

* When the ```mode``` in ```sky_archipelago_config.yaml``` is set to 2, the keyboard shortcuts are as follows.

<table>
    <tr>
      <th>key</th>
      <th>description</th>
    </tr>
    <tr align="left">
      <th>up arrow</th>
      <th>Move forward.</th>
    </tr>
    <tr align="left">
      <th>left arrow</th>
      <th>Turn left.</th>
    </tr>
    <tr align="left">
      <th>right arrow</th>
      <th>Turn right.</th>
    </tr>
    <tr align="left">
      <th>down arrow</th>
      <th>Move backward.</th>
    </tr>
    <tr align="left">
      <th>u</th>
      <th>Go up.</th>
    </tr>
    <tr align="left">
      <th>d</th>
      <th>Go down.</th>
    </tr>
</table>

* Other keyboard shortcuts are as follows.

<table>
    <tr>
      <th>key</th>
      <th>description</th>
    </tr>
    <tr>
      <th>Esc</th>
      <th align="left">Close the screen.</th>
    </tr>
    <tr>
      <th>t</th>
      <th align="left">Toggles physical object display on and off.</th>
    </tr>
    <tr>
      <th>w</th>
      <th align="left">Toggles wireframe display on and off.</th>
    </tr>
</table>

