import moderngl as mgl
from constants.colors import Colors
from constants.dimensions import SCREEN_DIMENSIONS
from constants.shape import Shape, SHAPE_VERTICES
from puzzles.puzzle_graph import PuzzleGraph
from engine.renderable import Renderable
from engine.camera import Camera
from models.polyhedron import Polyhedron


class TestScene(Renderable):
    def __init__(self, ctx: mgl.Context):
        self.ctx = ctx
        self.center = (
            SCREEN_DIMENSIONS[0] / 2,
            SCREEN_DIMENSIONS[1] / 2,
        )

    def init(self):
        self.camera = Camera(self.ctx)
        self.puzzle = PuzzleGraph.from_file_name("6_0")
        self.subject = Polyhedron(
            self.ctx, self.camera, SHAPE_VERTICES[Shape.tetrahedron], self.puzzle, "generic.png"
        )

    def handle_events(self, delta_time: int):
        self.subject.handle_events(delta_time)

    def render(self, delta_time: int):
        self.ctx.clear(color=Colors.WHITE)
        self.subject.render(delta_time)

    def destroy(self):
        self.subject.destroy()
