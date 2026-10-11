import cv2
import numpy as np
from panda3d.bullet import BulletRigidBodyNode
from panda3d.core import NodePath, PandaNode
from panda3d.core import Vec3, LColor, Point3
from panda3d.core import BitMask32

from islands.island_terrains import GeoMipIsland, ShaderMeshIsland
from islands.vegetation import Vegetation
from islands.town_builder import TownBuilder, Tree


# SkyArchipelago
class SkyIsland(NodePath):

    def __init__(self, name):
        super().__init__(BulletRigidBodyNode(name))
        self.node().set_mass(0)
        self.set_collide_mask(BitMask32.bit(1))


class GeoMipSkyIsland(SkyIsland):

    def __init__(self, name, heightfield_path, top_height=50, bottom_height=256):
        super().__init__(name)
        self.generate_island(heightfield_path, top_height, bottom_height)

    def generate_island(self, heightfield_path, top_height, bottom_height):
        heightfield_img = cv2.imread(heightfield_path)
        self.island = GeoMipIsland(self, heightfield_img, top_height, bottom_height)
        self.offset = Vec3(-self.island.size / 2, -self.island.size / 2, 0)

        town_builder = TownBuilder(
            tree=Tree(file_path='firtree/tree1.bam', scale=Vec3(3))
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

    def __init__(self, name, heightfield_path, top_height=50, bottom_height=256):
        super().__init__(name)
        self.generate_island(heightfield_path, top_height, bottom_height)

    def generate_island(self, heightfield_path, top_height, bottom_height):
        heightfield_img = cv2.imread(heightfield_path, cv2.IMREAD_UNCHANGED)
        self.island = ShaderMeshIsland(self, heightfield_img, top_height, bottom_height)
        self.offset = Vec3(-self.island.size / 2, -self.island.size / 2, 0)

        img = (heightfield_img >> 8).astype(np.uint8)
        img = np.repeat(img[:, :, np.newaxis], 3, axis=2)

        town_builder = TownBuilder(
            tree=Tree(file_path='firtree/tree1.bam', scale=Vec3(3))
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
        # heigtfield_path = 'images_8bit/island_heightmap_20260922121842.png'        
        heigtfield_path = 'images_8bit/island_heightmap_20260922121858.png'

        # heigtfield_path = 'images/img16_20260908001129.png'
        # self.build_town(heigtfield_path)
        # # self.buildings_root.set_pos(Point3(0, 0, 256 / 2 + 5))
        # self.buildings_root.set_pos(Point3(0, 0, 0))

        # island = ShaderMeshSkyIsland('island', heigtfield_path)
        island = GeoMipSkyIsland('island', heigtfield_path)
        island.reparent_to(base.render)
        base.world.attach(island.node())

        island.set_pos(Point3(320, -150, 40))
        # import pdb; pdb.set_trace()