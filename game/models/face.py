import numpy as np
import glm
import moderngl
import random

from constants.colors import Colors, BlendModes
from engine.vectors import normalize_vector
from engine.renderable import Renderable
from engine.camera import Camera
from engine.shader import get_shader_program
from engine.animation import AnimationLerper, AnimationLerpFunction, Animator
from engine.events import emit_event, FACE_ROTATED, block_events, allow_events
from puzzles.face_generator_definition import FaceGeneratorDefinition
from puzzles.puzzle_face import PuzzleFace
from models.types import Vertex, UV
from models.helpers import merge_collection_items

UNDERSIDE_NUDGE = (
    0.99  # To make sure there's not an overlap that causes rendering weirdness
)

PUZZLE_PATH_WIDTH = 0.1
RAD60 = np.radians(60)
SIN60 = np.sin(RAD60)
RAD30 = np.radians(30)
SIN30 = np.sin(RAD30)
COS30 = np.cos(RAD30)
TAN30 = np.tan(RAD30)
ACOS133 = np.arccos(1 / (3 * np.sqrt(3)))

CARVE_DEPTH = 0.03
FACE_NORMAL_DISTANCE = np.sqrt(1 / 3)

ROTATION_DURATION = 500  # ms
PULL_DURATION = 200 # ms
PULL_DISTANCE = 0.1

# This helps us render the lines above the face instead of inside it


class FaceCoordinateSystem:
    def __init__(
        self,
        face_generator_definition: FaceGeneratorDefinition,
        vertices: list[Vertex],
        uv_width: float,
    ):
        self.face_generator_definition = face_generator_definition

        uv_unit = uv_width * np.linalg.norm(np.subtract(vertices[1], vertices[0]))

        self.vertex_vectors = [np.array(vertex) for vertex in vertices]
        self.origin_vector = vertices[0]
        self.u_vector = normalize_vector(
            np.subtract(vertices[1], vertices[0]),
            uv_unit
        )

        middle_vector = np.array([0, 0, 0])
        self.segment_vectors = []
        self.clip_plane_normals = []
        for ix, vertex in enumerate(vertices):
            next_vertex_ix = ix + 1 if ix < len(vertices) - 1 else 0
            next_vertex = vertices[next_vertex_ix]
            self.segment_vectors.append(
                normalize_vector(np.subtract(next_vertex, vertex), uv_unit),
            )
            self.clip_plane_normals.append(np.cross(vertex, next_vertex))
            middle_vector = np.add(middle_vector, np.array(vertex) / len(vertices))

        self.normal_vector = normalize_vector(
            np.cross(self.segment_vectors[0], self.segment_vectors[1]),
            uv_unit,
        )

        self.v_vector = normalize_vector(
            np.cross(self.normal_vector, self.u_vector), uv_unit
        )

        self.rotation_angle = 360 / face_generator_definition.num_segments

    def _vector_outside_clip_bounds(self, vector: np.ndarray):
        for plane_ix, plane_normal in enumerate(self.clip_plane_normals):
            # Equation of a plane: Ax + By + Cz + D = 0
            res = np.sum([plane_normal[ix] * vector[ix] for ix in range(3)])
            if res > 0:
                return plane_ix
        return None

    def sink_vector(self, vector, sink_depth: float):
        sink_multiplier = (FACE_NORMAL_DISTANCE - sink_depth) / FACE_NORMAL_DISTANCE
        return vector * sink_multiplier

    def uv_coordinates_to_face_coordinates(self, uv_coordinates: UV, sink_depth=0):
        local_vector = np.add(
            np.multiply(uv_coordinates[0], self.u_vector),
            np.multiply(uv_coordinates[1], self.v_vector),
        )
        local_vector = np.add(self.origin_vector, local_vector)

        if sink_depth != 0:
            local_vector = self.sink_vector(local_vector, sink_depth)

        return local_vector



class Face(Renderable):
    def __init__(
        self,
        face_vertices: tuple[Vertex, Vertex, Vertex],
        puzzle_face: PuzzleFace,
        ctx: moderngl.Context,
        terrain_shader: moderngl.Program,
        carve_shader: moderngl.Program,
        wall_shader: moderngl.Program,
        underside_shader: moderngl.Program,
    ):
        self.face_vertices = face_vertices

        self.generator_definition = puzzle_face.generator_definition
        self.coordinate_system = FaceCoordinateSystem(
            puzzle_face.generator_definition, face_vertices, puzzle_face.generator_definition.segment_length
        )
        self.puzzle_face = puzzle_face
        self.depth = puzzle_face.depth

        self.rot_matrix = glm.mat4()
        self.pull_matrix = glm.mat4()

        self.is_puzzle_solved = False

        (terrain_vertices, terrain_uvs) = self.__make_terrain_vertices()
        self.terrain_shader_ref = terrain_shader
        self.terrain_buffer = self.__make_vbo_with_uv(ctx, terrain_vertices, terrain_uvs)
        self.terrain_vertex_array = self.__make_vao(
            ctx,
            self.terrain_shader_ref,
            [(self.terrain_buffer, "2f 3f", "in_textcoord_0", "in_position")],
        )

        [
            carve_vertices,
            wall_vertices,
            underside_vertices,
            carve_uvs,
        ] = self.__make_carve_vertices()
        self.has_carvings = len(carve_vertices) > 0
        if self.has_carvings:
            self.carve_shader_ref = carve_shader
            self.carve_buffer = self.__make_vbo_with_uv(ctx, carve_vertices, carve_uvs)
            self.carve_vertex_array = self.__make_vao(
                ctx, self.carve_shader_ref, [(self.carve_buffer, "2f 3f", "in_textcoord_0", "in_position")]
            )

            self.wall_shader_ref = wall_shader
            self.wall_buffer = self.__make_vbo(ctx, wall_vertices)
            self.wall_vertex_array = self.__make_vao(
                ctx, self.wall_shader_ref, [(self.wall_buffer, "3f", "in_position")]
            )

        self.underside_shader_ref = underside_shader
        self.underside_buffer = self.__make_vbo(ctx, underside_vertices)
        self.underside_vertex_array = self.__make_vao(
            ctx, self.underside_shader_ref, [(self.underside_buffer, "3f", "in_position")]
        )

        self.nv = glm.vec3(self.coordinate_system.normal_vector)
        self.rotation_animator = Animator(
            lerper=AnimationLerper(
                AnimationLerpFunction.ease_in_out,
                ROTATION_DURATION,
            ),
            start_value=0,
            on_stop=self.__stop_rotation,
        )
        self.pull_animator = Animator(
            lerper=AnimationLerper(
                AnimationLerpFunction.ease_in_out,
                PULL_DURATION,
            ),
            start_value=0,
        )

    def __make_terrain_vertices(self):
        polygons = self.puzzle_face.polygons
        polygon_vertices = []
        polygon_uvs = []
        # Render polygons on outside faces
        for polygon in polygons:
            if polygon.is_active:
                continue
            for node in polygon.nodes:
                polygon_vertices.append(
                    self.coordinate_system.uv_coordinates_to_face_coordinates(
                        node.uv_coordinates
                    )
                )
                polygon_uvs.append(node.uv_coordinates)
        return (polygon_vertices, polygon_uvs)

    def __make_carve_vertices(self):
        active_polygons = self.puzzle_face.active_polygons
        active_polygon_vertices = []
        active_polygon_uvs = []
        wall_vertices = []
        underside_inner_vertices = [
            None
        ] * self.generator_definition.vertex_count_for_ring(self.depth)
        for polygon in active_polygons:
            # basin
            for node in polygon.nodes:
                top_coordinates = (
                    self.coordinate_system.uv_coordinates_to_face_coordinates(
                        node.uv_coordinates
                    )
                )
                bottom_coordinates = (
                    self.coordinate_system.uv_coordinates_to_face_coordinates(
                        node.uv_coordinates, CARVE_DEPTH
                    )
                )
                active_polygon_vertices.append(bottom_coordinates)
                active_polygon_uvs.append(node.uv_coordinates)
                count_idx = node.indices[1]
                if node.is_edge:
                    if underside_inner_vertices[count_idx] is None:
                        underside_inner_vertices[count_idx] = [
                            top_coordinates,
                            bottom_coordinates,
                        ]

            # walls
            inactive_neighbor_lines = polygon.get_inactive_neighbor_lines()
            for inactive_line_nodes in inactive_neighbor_lines:
                terrain_coordinates = [
                    self.coordinate_system.uv_coordinates_to_face_coordinates(
                        node.uv_coordinates
                    )
                    for node in inactive_line_nodes
                ]
                carve_coordinates = [
                    self.coordinate_system.sink_vector(coordinates, CARVE_DEPTH)
                    for coordinates in terrain_coordinates
                ]
                quad_triangles = [
                    terrain_coordinates[0],
                    terrain_coordinates[1],
                    carve_coordinates[0],
                    carve_coordinates[1],
                    carve_coordinates[0],
                    terrain_coordinates[1],
                ]
                wall_vertices.extend([v for v in quad_triangles])

        # Underside
        underside_vertices = [np.array([0, 0, 0])]
        for ix, vertex in enumerate(self.face_vertices):
            underside_vertices.append(vertex)
            vertex_range = self.generator_definition.vertex_range_for_segment(
                ix, self.depth, extra=1
            )
            top_first = True
            for count_idx in vertex_range:
                if count_idx == len(underside_inner_vertices):
                    count_idx = 0
                underside_wall_vertices = underside_inner_vertices[count_idx]
                if not underside_wall_vertices:
                    continue
                if not top_first:
                    next_count_idx = (
                        count_idx + 1
                        if count_idx < len(underside_inner_vertices) - 1
                        else 0
                    )
                    if underside_inner_vertices[next_count_idx]:
                        underside_vertices.append(underside_wall_vertices[1])
                        continue
                    underside_wall_vertices.reverse()
                underside_vertices.extend(underside_wall_vertices)
                top_first = not top_first
        underside_vertices.append(self.face_vertices[0])
        underside_vertices = np.array(underside_vertices) * UNDERSIDE_NUDGE

        return (active_polygon_vertices, wall_vertices, underside_vertices, active_polygon_uvs)

    def __make_vao(self, ctx, shader, context):
        return ctx.vertex_array(shader, context)

    def __make_vbo(self, ctx, vertices):
        return ctx.buffer(np.array(vertices, dtype="f4"))

    def __make_vbo_with_uv(self, ctx, vertices, uvs):
        return self.__make_vbo(ctx, merge_collection_items(uvs, vertices))

    def __rotate_by_rotations(self, rotations):
        rotation_angle = self.coordinate_system.rotation_angle * rotations
        self.rot_matrix = glm.rotate(glm.mat4(), glm.radians(rotation_angle), self.nv)

    def __pull_by_distance(self, pull_distance):
        if pull_distance == 0:
            self.pull_matrix = glm.mat4x4()
        else:
            self.pull_matrix = glm.translate(
                normalize_vector(-self.nv, pull_distance)
            )

    def __stop_rotation(self, rotations):
        self.__rotate_by_rotations(rotations)
        self.puzzle_face.rotate(rotations % len(self.coordinate_system.segment_vectors))
        emit_event(FACE_ROTATED, {})

    def renderFace(self, camera: Camera, model_matrix, delta_time):
        if self.rotation_animator.is_animating:
            rotations = self.rotation_animator.frame(delta_time)
            self.__rotate_by_rotations(rotations)

        if self.pull_animator.is_animating:
            pull_distance = self.pull_animator.frame(delta_time)
            self.__pull_by_distance(pull_distance)


        m_mvp = camera.view_projection_matrix * model_matrix * self.rot_matrix * self.pull_matrix
        self.terrain_shader_ref["m_mvp"].write(m_mvp)
        self.terrain_shader_ref["v_nv"].write(self.nv)
        self.terrain_vertex_array.render()

        if self.is_puzzle_solved:
            return # don't render path when exploding

        if self.has_carvings:
            self.carve_shader_ref["m_mvp"].write(m_mvp)
            self.carve_vertex_array.render()
            self.wall_shader_ref["m_mvp"].write(m_mvp)
            self.wall_vertex_array.render()

        self.underside_shader_ref["m_mvp"].write(m_mvp)
        self.underside_vertex_array.render(mode=moderngl.TRIANGLE_FAN)

        # self.rotation_animator.frame(delta_time)

    def rotate(self, num_rotations=1):
        self.rotation_animator.start(
            self.rotation_animator.current_value + num_rotations
        )

    def pull(self):
        self.pull_animator.start(PULL_DISTANCE)

    def push(self):
        self.pull_animator.start(0)

    def scramble(self):
        num_rotations = random.randint(0, len(self.coordinate_system.segment_vectors))
        if num_rotations == 0: # Roll Again to decrease the odds of zero to 1/9
            num_rotations = random.randint(0, len(self.coordinate_system.segment_vectors))
        self.rotate(num_rotations)

    def explode(self):
        self.is_puzzle_solved = True

    def reset(self):
        self.pull_animator.set(0)
        self.rotation_animator.set(0)
        self.is_puzzle_solved = False

    def destroy(self):
        self.terrain_buffer.release()
        self.terrain_vertex_array.release()

    def projected_vertices(self, matrix) -> list[glm.vec4]:
        # This returns a vec4 in clip space
        return [
            matrix * self.rot_matrix * glm.vec4(vertex, 1.0)
            for vertex in self.face_vertices
        ]
