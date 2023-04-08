# Example file showing a basic pygame "game loop"
import pygame
import moderngl as mgl
from constants.dimensions import SCREEN_DIMENSIONS
from scenes.gameplay_scene import GameplayScene
from engine.events import LEVEL_WON

MAX_FPS = 60

# Setup
pygame.init()
clock = pygame.time.Clock()

# Set OpenGL Attributes and create opengl-enabled screen
pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
pygame.display.gl_set_attribute(
    pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE
)


class Main:
    def __init__(self):
        self.screen = pygame.display.set_mode(
            SCREEN_DIMENSIONS,
            flags=pygame.OPENGL | pygame.DOUBLEBUF | pygame.GL_CONTEXT_DEBUG_FLAG,
        )
        self.ctx = mgl.create_context()  # OpenGL
        self.ctx.enable(flags=mgl.DEPTH_TEST)
        self.scene = GameplayScene(self.ctx)
        self.scene.init()
        self.delta_time = 0  # Time since last frame

    def quit(self):
        self.scene.destroy()
        pygame.quit()
        exit()

    def handle_events(self) -> None:
        if pygame.event.get(pygame.QUIT):
            self.quit()
        self.scene.handle_events(self.delta_time)

    def render(self) -> None:
        self.scene.render(self.delta_time)
        pygame.display.flip()

    def run(self):
        while True:
            self.handle_events()
            self.render()
            self.delta_time = clock.tick(MAX_FPS)


Main().run()
