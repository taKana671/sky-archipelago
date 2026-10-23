import itertools
import sys
from enum import Enum, auto, IntEnum

from direct.showbase.ShowBase import ShowBase
from direct.showbase.ShowBaseGlobal import globalClock
from direct.showbase.InputStateGlobal import inputState
from direct.interval.IntervalGlobal import Sequence, Func
from direct.stdpy import threading
from panda3d.bullet import BulletWorld, BulletDebugNode
from panda3d.core import Point3, Vec3, Vec2, Quat
from panda3d.core import Quat, look_at
from panda3d.core import NodePath
from panda3d.core import AntialiasAttrib, TransparencyAttrib
from panda3d.core import load_prc_file_data

from scene import Scene
from viewer import Viewer, Motions
# from spinner.spinner_dots import SpinnerDots


# load_prc_file_data("", """
#     textures-power-2 none
#     gl-coordinate-system default
#     window-title Panda3D Voronoi City3
#     filled-wireframe-apply-shader true
#     stm-max-views 8
#     stm-max-chunk-count 2048
#     framebuffer-multisample 1
#     multisamples 2
#     load-file-type p3assimp""")


load_prc_file_data("", """
    textures-power-2 none
    gl-coordinate-system default
    window-title Panda3D SkyArchipelago
    filled-wireframe-apply-shader true
    stm-max-views 8
    stm-max-chunk-count 2048
    framebuffer-multisample 1
    multisamples 2""")


DO_POSITIONING = False


class Status(Enum):

    SCREEN_CHANGE = auto()
    SCREEN_WAITING = auto()
    ACTIVE = auto()
    SCENE_CREATE = auto()
    SCENE_WAITING = auto()
    SPINNER_FINISH = auto()
    SCENE_COMPLETE = auto()


class View(Enum):

    SKY = auto()
    GROUND = auto()


class Mode(IntEnum):

    FIXED_CAMERA = 1
    FOLLOW_CAMERA = 2
    ROTATE_CAMERA = 3

    @classmethod
    def convert_to_str(cls):
        return ', '.join([f'{mem.name}: {mem.value}' for mem in cls])


class SkyArchipelago(ShowBase):

    def __init__(self, mode=1):
        super().__init__()
        self.disable_mouse()
        self.render.set_antialias(AntialiasAttrib.MAuto)

        self.world = BulletWorld()
        self.world.set_gravity(Vec3(0, 0, -9.81))
        self.debug = self.render.attach_new_node(BulletDebugNode('debug'))
        self.world.set_debug_node(self.debug.node())

        self.scene = Scene()
        self.scene.reparent_to(self.render)

        self.mode = mode
        self.initialize_for_mode()


        # self.status = Status.SCENE_CREATE
        self.status = Status.ACTIVE
        self.view = View.SKY

        self.accept('escape', sys.exit)
        self.accept('t', self.toggle_debug)
        self.accept('w', self.toggle_wireframe)

        if DO_POSITIONING:
            self.setup_positioning()

        self.taskMgr.add(self.update, 'update')

    def init_rotate_camera_mode(self):
        self.accept('mouse1', self.mouse_click)
        self.accept('mouse1-up', self.mouse_release)
        self.clicked = False
        self.dragging = False
        self.before_mouse_pos = None
        self.screen_changed = False

    def init_follow_camera_mode(self):
        inputState.watch_with_modifiers(Motions.FORWARD, 'arrow_up')
        inputState.watch_with_modifiers(Motions.BACKWARD, 'arrow_down')
        inputState.watch_with_modifiers(Motions.LEFT, 'arrow_left')
        inputState.watch_with_modifiers(Motions.RIGHT, 'arrow_right')
        inputState.watch_with_modifiers(Motions.DOWN, 'd')
        inputState.watch_with_modifiers(Motions.UP, 'u')

    def get_hpr_from_lookat(self, current_pos, target_pos):
        direction = target_pos - current_pos
        quat = Quat()
        look_at(quat, direction, Vec3.up())
        hpr = quat.get_hpr()
        return hpr

    def setup_fixed_camera(self, camera_pos, look_pos, fov):
        self.camera.set_pos(camera_pos)
        self.floater = NodePath('floater')
        self.floater.set_pos(look_pos)
        self.floater.reparent_to(self.render)
        self.camera.look_at(self.floater)
        self.camLens.set_fov(fov)

    def setup_follow_camera(self, camera_pos, look_pos, fov):
        hpr = self.get_hpr_from_lookat(camera_pos, look_pos)
        self.viewer = Viewer()
        self.viewer.set_pos_hpr(camera_pos, hpr)
        self.viewer.reparent_to(self.render)
        self.camera.reparent_to(self.viewer)
        self.camLens.set_fov(fov)

    def setup_rotate_camera(self, camera_pos, look_pos, fov, near=1):
        self.camera_root = NodePath('camera_root')
        self.camera_root.reparent_to(self.render)

        self.camera.reparent_to(self.camera_root)
        self.camera.set_pos(camera_pos)
        self.camera.look_at(look_pos)

        self.camLens.set_fov(fov)
        self.camLens.set_near_far(near, 100000)

    def initialize_for_mode(self):
        fov = 30

        match self.mode:
            case Mode.FIXED_CAMERA | Mode.FOLLOW_CAMERA:
                camera_pos = Point3(180, -700, 30)
                look_pos = Point3(-84, 80, -8)

                if self.mode == Mode.FIXED_CAMERA:
                    self.setup_fixed_camera(camera_pos, look_pos, fov)
                else:
                    self.setup_follow_camera(camera_pos, look_pos, fov)
                    self.init_follow_camera_mode()

            case Mode.ROTATE_CAMERA:
                camera_pos = Point3(-400, -400, 200)
                look_pos = Point3(0, 0, 0)
                self.setup_rotate_camera(camera_pos, look_pos, fov)
                self.init_rotate_camera_mode()

            case _:
                raise ValueError(
                    f'Invalid value: {self.mode}; '
                    f'Valid values: {Mode.convert_to_str()}.'
                )

    def setup_positioning(self):
        if self.mode != Mode.FIXED_CAMERA:
            raise ValueError(
                'To position an object, '
                f'specify mode {Mode.FIXED_CAMERA.value} ({Mode.FIXED_CAMERA.name})'
            )

        targets = [
            ('floater', self.floater),
            ('camera', self.camera),
            *[(name, island) for name, island in self.scene.islands.items()]
        ]
        self.positioning_targets = itertools.cycle(targets)
        self.change_positioning_target()
        self.accept('n', self.change_positioning_target)
        self.accept('x', self.positioning, ['x', 1])
        self.accept('shift-x', self.positioning, ['x', -1])
        self.accept('y', self.positioning, ['y', 1])
        self.accept('shift-y', self.positioning, ['y', -1])
        self.accept('z', self.positioning, ['z', 1])
        self.accept('shift-z', self.positioning, ['z', -1])
        self.accept('h', self.positioning, ['h', 1])
        self.accept('shift-h', self.positioning, ['h', -1])
        self.accept('p', self.positioning, ['p', 1])
        self.accept('shift-p', self.positioning, ['p', -1])
        self.accept('r', self.positioning, ['r', 1])
        self.accept('shift-r', self.positioning, ['r', -1])

    def change_positioning_target(self):
        self.target_name, self.target = next(self.positioning_targets)
        print('The positioning target has been set to:', self.target_name)

    def positioning(self, key, direction):
        distance = 1
        angle = 5
        pos = Point3()
        hpr = Vec3()

        match key:
            case 'x':
                pos.x = distance * direction

            case 'y':
                pos.y = distance * direction

            case 'z':
                pos.z = distance * direction

            case 'h':
                hpr.x = angle * direction

            case 'p':
                hpr.y = angle * direction

            case 'r':
                hpr.x = angle * direction

        pos = self.target.get_pos() + pos
        hpr = self.target.get_hpr() + hpr
        self.target.set_pos_hpr(pos, hpr)
        print(f'{self.target_name} has been changed to; pos: {pos}, hpr: {hpr}')

    def toggle_debug(self):
        if self.debug.is_hidden():
            self.debug.show()
        else:
            self.debug.hide()

    # def toggle_view(self):
    #     self.status = Status.SCREEN_CHANGE

    # def fade_camera(self, duration=2.0):
    #     config = self.ground_config if self.view == View.SKY else self.sky_config
    #     self.screen_changed = False

    #     props = self.win.get_properties()
    #     size = props.get_size()
    #     buffer = self.win.make_texture_buffer('tex_buffer', *size)
    #     buffer.set_clear_color_active(True)
    #     buffer.set_clear_color((0.5, 0.5, 0.5, 1.0))

    #     temp_cam = self.make_camera(buffer)
    #     temp_cam.node().get_lens().set_fov(config.fov)
    #     temp_cam.set_pos(config.pos)
    #     temp_cam.look_at(config.look_at)
    #     temp_cam.reparent_to(config.parent)

    #     card = buffer.get_texture_card()
    #     card.reparent_to(self.render2d)
    #     card.set_transparency(TransparencyAttrib.M_alpha)
    #     # card.set_transparency(TransparencyAttrib.M_multisample)

    #     Sequence(
    #         card.colorScaleInterval(duration, 1, 0, blendType='easeInOut'),
    #         Func(config.switch_func),
    #         Func(card.remove_node),
    #         Func(self.graphicsEngine.remove_window, buffer),
    #         Func(self.end_fade)
    #     ).start()

    # def view_while_moving(self):
    #     """Use the keyboard to move around the city.
    #     """
    #     self.viewer.set_pos(self.ground_config.pos)
    #     self.viewer.look_at(self.ground_config.look_at)

    #     self.camera.set_pos_hpr(Point3(0, 0, 0), Vec3(0, 0, 0))
    #     self.camera.reparent_to(self.viewer)

    #     self.camLens.set_fov(self.ground_config.fov)
    #     self.camLens.set_near_far(self.ground_config.near, 100000)

    # def view_from_sky(self):
    #     """View the city from above and rotate it by dragging the mouse.
    #     """
    #     self.camera.reparent_to(self.camera_root)
    #     self.camera.set_pos(self.sky_config.pos)
    #     self.camera.look_at(self.sky_config.look_at)

    #     self.camLens.set_fov(self.sky_config.fov)
    #     self.camLens.set_near_far(self.sky_config.near, 100000)

    def end_fade(self):
        self.screen_changed = True

    def mouse_click(self):
        self.dragging = True
        self.dragging_start_time = globalClock.get_frame_time()

    def mouse_release(self):
        if globalClock.get_frame_time() - self.dragging_start_time < 0.2:
            self.clicked = True

        self.dragging = False
        self.before_mouse_pos = None

    def rotate_camera(self, mouse_pos, dt):
        if self.before_mouse_pos:
            angle = Vec3()

            if (delta := mouse_pos.x - self.before_mouse_pos.x) < 0:
                angle.x += 180
            elif delta > 0:
                angle.x -= 180

            if (delta := mouse_pos.y - self.before_mouse_pos.y) < 0:
                angle.z -= 180
            elif delta > 0:
                angle.z += 180

            angle *= dt
            self.camera_root.set_hpr(self.camera_root.get_hpr() + angle)

        self.before_mouse_pos = Vec2(mouse_pos.xy)

    def watch_keyboard(self):
        direction = Vec3()

        if inputState.is_set(Motions.FORWARD):
            direction.y += 1

        if inputState.is_set(Motions.BACKWARD):
            direction.y -= 1

        if inputState.is_set(Motions.LEFT):
            direction.x += 1

        if inputState.is_set(Motions.RIGHT):
            direction.x -= 1

        if inputState.is_set(Motions.UP):
            direction.z += 1

        if inputState.is_set(Motions.DOWN):
            direction.z -= 1

        return direction

    def update(self, task):
        dt = globalClock.get_dt()

        match self.status:

            case Status.SCREEN_CHANGE:
                self.fade_camera()
                self.status = Status.SCREEN_WAITING

            case Status.SCREEN_WAITING:
                if self.screen_changed:
                    self.view = View.GROUND if self.view == View.SKY else View.SKY
                    self.status = Status.ACTIVE

            case Status.ACTIVE:
                if self.mode == Mode.FOLLOW_CAMERA:
                    direction = self.watch_keyboard()
                    self.viewer.control(direction, dt)

                elif self.mode == Mode.ROTATE_CAMERA:
                    if self.mouseWatcherNode.has_mouse():
                        mouse_pos = self.mouseWatcherNode.get_mouse()

                        if self.dragging:
                            if globalClock.get_frame_time() - self.dragging_start_time >= 0.2:
                                self.rotate_camera(mouse_pos, dt)

            # case Status.SCENE_CREATE:
            #     self.spinner = SpinnerDots(dot_color=(1., 1., 1., .8))
            #     self.scene_create_thread = threading.Thread(target=self.scene.setup_scene)
            #     self.scene_create_thread.start()
            #     self.status = Status.SCENE_WAITING

            # case Status.SCENE_WAITING:
            #     self.spinner.update()

            #     if not self.scene_create_thread.is_alive():
            #         self.status = Status.SPINNER_FINISH

            # case Status.SPINNER_FINISH:
            #     if self.spinner.finish():
            #         self.spinner.destroy()
            #         self.status = Status.SCENE_COMPLETE

            # case Status.SCENE_COMPLETE:
            #     self.scene.reparent_to(self.render)
            #     self.status = Status.ACTIVE
        self.scene.sky.update(self.camera.get_pos(self.render))

        self.world.do_physics(dt)
        return task.cont


if __name__ == '__main__':
    app = SkyArchipelago()
    app.run()