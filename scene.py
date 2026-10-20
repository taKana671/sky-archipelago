import cv2
import numpy as np
from panda3d.bullet import BulletRigidBodyNode
from panda3d.core import NodePath, PandaNode
from panda3d.core import Vec3, LColor, Point3
from panda3d.core import BitMask32
from panda3d.core import Shader, Fog
from panda3d.core import TransparencyAttrib
from panda3d.core import AmbientLight, DirectionalLight

from islands.island_terrains import GeoMipIsland, ShaderMeshIsland
from islands.town_builder import TownBuilder, Tree
from islands.vegetation import Vegetation
from shapes import Plane, Sphere


class SkyIsland(NodePath):

    def __init__(self, name):
        super().__init__(BulletRigidBodyNode(name))
        self.node().set_mass(0)
        self.set_collide_mask(BitMask32.bit(1))


class GeoMipSkyIsland(SkyIsland):

    def __init__(self, name, heightfield_path, top_height=50, bottom_height=256, **kwargs):
        super().__init__(name)
        self.generate_island(heightfield_path, top_height, bottom_height, **kwargs)

    def generate_island(self, heightfield_path, top_height, bottom_height, **kwargs):
        heightfield_img = cv2.imread(heightfield_path)
        self.island = GeoMipIsland(self, heightfield_img, top_height, bottom_height)
        self.offset = Vec3(-self.island.size / 2, -self.island.size / 2, 0)

        town_builder = TownBuilder(
            tree=Tree(file_path='firtree/tree1.bam', scale=Vec3(3)),
            building_max_stories=kwargs.get('max_stories', 4)
        )
        self.town_raw_center, self.town_radius = town_builder.generate(self, heightfield_img)

        vegetation = Vegetation(
            model_path="plants1/plants1.egg",
            model_scale=Vec3(0.3),
            color_scale=LColor(1.2, 1.8, 1.4, 1.0),
        )
        vegetation.generate(self, heightfield_img)

        vegetation = Vegetation(
            model_path="daisy/daisy.egg",
            model_scale=Vec3(12),
            base_density=0.02
        )
        vegetation.generate(self, heightfield_img)


class ShaderMeshSkyIsland(SkyIsland):

    def __init__(self, name, heightfield_path, top_height=50, bottom_height=256, **kwargs):
        super().__init__(name)
        self.generate_island(heightfield_path, top_height, bottom_height, **kwargs)

    def generate_island(self, heightfield_path, top_height, bottom_height, **kwargs):
        heightfield_img = cv2.imread(heightfield_path, cv2.IMREAD_UNCHANGED)
        self.island = ShaderMeshIsland(self, heightfield_img, top_height, bottom_height)
        self.offset = Vec3(-self.island.size / 2, -self.island.size / 2, 0)

        img = (heightfield_img >> 8).astype(np.uint8)
        img = np.repeat(img[:, :, np.newaxis], 3, axis=2)

        town_builder = TownBuilder(
            tree=Tree(file_path='firtree/tree1.bam', scale=Vec3(3)),
            building_max_stories=kwargs.get('max_stories', 4)
        )
        self.town_raw_center, self.town_radius = town_builder.generate(self, img)

        vegetation = Vegetation(
            model_path="plants1/plants1.egg",
            model_scale=Vec3(0.3),
            color_scale=LColor(1.2, 1.8, 1.4, 1.0),
        )
        vegetation.generate(self, img)

        vegetation = Vegetation(
            model_path="daisy/daisy.egg",
            model_scale=Vec3(12),
            base_density=0.02
        )
        vegetation.generate(self, img)


class Clouds(NodePath):

    def __init__(self, sun_dir, plane_center, size=6000):
        super().__init__(PandaNode('clouds'))
        self.plane = Plane(
            width=size,
            depth=size,
            segs_d=100,
            segs_w=100).create()

        self.plane.reparent_to(self)
        self.set_transparency(TransparencyAttrib.M_alpha)
        self.setup_shader(sun_dir, plane_center)

    def setup_shader(self, sun_dir, plane_center):
        shader = Shader.load(Shader.SL_GLSL, 'shaders/clouds_v.glsl', 'shaders/clouds_f.glsl')
        self.plane.set_shader(shader)

        self.plane.set_shader_input('sun_direction', sun_dir)
        self.plane.set_shader_input('camera', base.camera)
        self.plane.set_shader_input('plane_center', plane_center)


class Sky(NodePath):

    def __init__(self, sun_dir):
        super().__init__(PandaNode('sky'))
        self.sphere = Sphere(radius=100.0).create()
        self.sphere.reparent_to(self)
        self.sphere.set_bin('background', 0)
        self.sphere.set_depth_write(False)
        self.sphere.set_light_off()
        self.sphere.set_fog_off()
        self.setup_shader(sun_dir)

    def setup_shader(self, sun_dir):
        shader = Shader.load(Shader.SL_GLSL, 'shaders/sky_v.glsl', 'shaders/sky_f.glsl')
        self.sphere.set_shader(shader)
        self.sphere.set_shader_input('sun_direction', sun_dir)

    def update(self, pos):
        self.set_pos(pos)


class Scene(NodePath):

    def __init__(self):
        super().__init__(PandaNode('scene'))
        self.islands = [island for island in self.generate_islands()]
        self.generate_sky()
        self.setup_light()

    def generate_sky(self):
        # Setup fog.
        self.fog = Fog('scene_fog')
        self.fog.set_color(0.65, 0.82, 0.95)
        self.fog.set_exp_density(0.00015)
        base.render.set_fog(self.fog)

        sun_dir = Vec3(1.0, 1.0, 0.5).normalized()
        plane_center = Point3(-372, 1942, -300)

        # Create clouds.
        clouds = Clouds(sun_dir, plane_center)
        clouds.set_pos(plane_center)
        clouds.reparent_to(self)

        # Create sky.
        self.sky = Sky(sun_dir)
        self.sky.reparent_to(self)

    def generate_islands(self):
        islands_details = [
            ('8bit_island_heightmap_4.png', Point3(15, -515, -45), Vec3(545, 0, 0), dict(max_stories=3)),
            ('8bit_island_heightmap_1.png', Point3(-10, 30, 0), Vec3(0, 0, 0), None),
            ('8bit_island_heightmap_2.png', Point3(-734, 1096, 160), Vec3(270, 0, 0), None),
            ('8bit_island_heightmap_3.png', Point3(-1609, 4400, 635), Vec3(100, 0, 0), None)
        ]

        for i, (file_name, pos, hpr, extra_args) in enumerate(islands_details):
            kwargs = extra_args if extra_args is not None else {}
            island = GeoMipSkyIsland(f'island_{i}', f'images/{file_name}', **kwargs)
            island.set_pos_hpr(pos, hpr)
            island.reparent_to(base.render)
            base.world.attach(island.node())
            yield island

    def setup_light(self):
        ambient_light = NodePath(AmbientLight('ambient_light'))
        ambient_light.reparent_to(base.render)
        ambient_light.node().set_color(LColor(0.6, 0.6, 0.6, 1.0))
        base.render.set_light(ambient_light)

        directional_light = NodePath(DirectionalLight('directional_light'))
        directional_light.node().get_lens().set_film_size(200, 200)
        directional_light.node().get_lens().set_near_far(1, 100)
        directional_light.node().set_color(LColor(1, 1, 1, 1))
        directional_light.set_pos_hpr(Point3(0, 0, 180), Vec3(-30, -45, 0))
        directional_light.node().show_frustum()
        base.render.set_light(directional_light)
        directional_light.node().set_shadow_caster(True)
        base.render.set_shader_auto()