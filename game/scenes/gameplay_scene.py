import moderngl
import pygame
import glm

from constants.colors import Colors, set_opacity, BlendModes, ShapeStyle
from constants.dimensions import SCREEN_DIMENSIONS
from constants.shape import Shape, SHAPE_VERTICES
from ui.image_plane import ImagePlane
from ui.next_button import NextButton
from puzzles.puzzle_graph import PuzzleGraph
from engine.camera import Camera
from engine.events import NEXT_PUZZLE, emit_event, FADE_IN, FADE_OUT, FADED_OUT, PUZZLE_SOLVED, NEXT_LEVEL
from engine.renderable import Renderable
from models.polyhedron import Polyhedron
from ui.progress import Progress
from scenes.gameplay_levels import LEVELS


class GameplayScene(Renderable):
    def __init__(self, ctx: moderngl.Context, camera: Camera):
        self.ctx = ctx
        self.camera = camera
        self.center = (
            SCREEN_DIMENSIONS[0] / 2,
            SCREEN_DIMENSIONS[1] / 2,
        )

        self.current_level_index = 0
        self.current_puzzle_index = 0
        self._load_puzzles()

        self.progress = Progress(self.ctx, camera.view_projection_matrix)
        self.next_button = NextButton(
            self.ctx,
            self.camera.view_projection_matrix,
            glm.vec3(0, 1.1, -2.1),
            on_click=self._go_to_next_puzzle
        )
        self.show_next_button = False
        self.is_last_puzzle_on_level = False

    def _go_to_next_puzzle(self):
        if self.show_next_button:
            if self.is_last_puzzle_on_level:
                self.current_puzzle().explode()
            else:
                emit_event(NEXT_PUZZLE, {})

    def init(self):
        self._start_puzzle()

    def _load_puzzles(self):
        level = LEVELS[self.current_level_index]
        self.puzzles = []
        puzzles_in_level = level['puzzles']
        puzzles_count = len(puzzles_in_level)
        for index, puzzle in enumerate(puzzles_in_level):
            level_poly = Polyhedron(
                self.ctx,
                self.camera,
                SHAPE_VERTICES[level["shape"]],
                PuzzleGraph.from_file_name(puzzle),
                style=level["style"]
            )
            level_poly.scramble()
            self.puzzles.append(level_poly)


    def _start_puzzle(self):
        emit_event(FADE_IN)
        self.current_puzzle().introduce()

    def _end_puzzle(self):
        emit_event(FADE_OUT)

    def current_puzzle(self):
        return self.puzzles[self.current_puzzle_index]

    def advance(self):
        self.current_puzzle().destroy()
        self.show_next_button = False
        puzzles_count = len(self.puzzles)
        if self.current_puzzle_index < puzzles_count - 1: # next puzzle
            self.current_puzzle_index += 1
            self.is_last_puzzle_on_level = self.current_puzzle_index == puzzles_count - 1
            self._start_puzzle()
        elif self.current_level_index < len(LEVELS) - 1: # next level
            for puzzle in self.puzzles:
                puzzle.destroy()
            self.current_puzzle_index = 0
            self.current_level_index += 1
            self.progress.reset()
            self._load_puzzles()
            self._start_puzzle()
        else:
            print("GAME WOM")

    def handle_event(self, event: pygame.event.Event, world_time: int):
        if event.type == PUZZLE_SOLVED:
            self.progress.complete_puzzle(self.current_puzzle_index)
            self.show_next_button = True
        elif event.type == NEXT_PUZZLE:
            self._end_puzzle()
        elif event.type == FADED_OUT or event.type == NEXT_LEVEL:
            if self.current_puzzle().is_puzzle_solved:
                self.advance()

        if self.current_puzzle().is_alive:
            self.current_puzzle().handle_event(event, world_time)
        
        self.next_button.handle_event(event, world_time)

    def render(self, delta_time: int):
        if self.current_puzzle().is_alive:
            self.current_puzzle().render(delta_time)
        self.progress.render(delta_time)    
        if self.show_next_button:
            self.next_button.render(delta_time)

    def destroy(self):
        self.progress.destroy()
        for puzzle in self.puzzles:
            puzzle.destroy()
