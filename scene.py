import cv2
import numpy as np
from panda3d.bullet import BulletRigidBodyNode
from panda3d.core import NodePath, PandaNode
from panda3d.core import Vec3, LColor, Point3
from panda3d.core import BitMask32

from islands.island_terrains import GeoMipIsland, ShaderMeshIsland
from islands.vegetation import Vegetation
from islands.town_builder import TownBuilder, Tree


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


class Scene(NodePath):

    def __init__(self):
        super().__init__(PandaNode('scene'))
        self.islands = [island for island in self.generate_islands()]

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
    
    # def generate_islands(self):
    #     islands_details = [
    #         ('16bit_island_heightmap_1.png', Point3(15, -515, -45), Vec3(545, 0, 0), dict(max_stories=3)),
    #         ('16bit_island_heightmap_2.png', Point3(-10, 30, 0), Vec3(0, 0, 0), None),
    #         ('16bit_island_heightmap_3.png', Point3(-734, 1096, 160), Vec3(270, 0, 0), None),
    #         ('16bit_island_heightmap_4.png', Point3(-1609, 4400, 635), Vec3(100, 0, 0), None)
    #     ]

    #     for i, (file_name, pos, hpr, extra_args) in enumerate(islands_details):
    #         kwargs = extra_args if extra_args is not None else {}
    #         island = ShaderMeshSkyIsland(f'island_{i}', f'images/{file_name}', **kwargs)
    #         island.set_pos_hpr(pos, hpr)
    #         island.reparent_to(base.render)
    #         base.world.attach(island.node())
    #         yield island