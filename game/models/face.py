import numpy as np
import glm
import moderngl

from constants.colors import Colors
from engine.vectors import normalize_vector
from engine.renderable import Renderable
from engine.camera import Camera
from engine.shader import get_shader_program
from engine.animation import AnimationLerper, AnimationLerpFunction, Animator
from engine.events import emit_event, FACE_ROTATED
from puzzles.face_generator_definition import FaceGeneratorDefinition
from puzzles.puzzle_node import PuzzleNode
from puzzles.puzzle_face import PuzzleFace
from models.types import Vertex, UV
from models.helpers import merge_collection_items

WALL_COLOR = Colors.CHARCOAL
BASE_LINE_COLOR = glm.vec3(Colors.WHITE)
LINE_LUMINOSITY_INACTIVE = 0.5
LINE_LUMINOSITY_ACTIVE = 1.0
DEFAULT_LINE_COLOR = BASE_LINE_COLOR * LINE_LUMINOSITY_INACTIVE

PUZZLE_PATH_WIDTH = 0.1
RAD60 = np.radians(60)
SIN60 = np.sin(RAD60)
RAD30 = np.radians(30)
SIN30 = np.sin(RAD30)
COS30 = np.cos(RAD30)
TAN30 = np.tan(RAD30)
ACOS133 = np.arccos(1 / (3 * np.sqrt(3)))

CARVE_DEPTH = 0.05
FACE_NORMAL_DISTANCE = np.sqrt(1/3)

ROTATION_DURATION = 500 # ms
LUMINATION_DURATION = 1000 # ms

# This helps us render the lines above the face instead of inside it

class FaceCoordinateSystem:

  def __init__(
    self,
    face_generator_definition: FaceGeneratorDefinition,
    vertices: list[Vertex],
  ):
    self.face_generator_definition = face_generator_definition

    self.vertex_vectors = [np.array(vertex) for vertex in vertices]
    self.origin_vector = vertices[0]
    self.u_vector = np.subtract(vertices[1], vertices[0])
    segment_vector_mag = np.linalg.norm(self.u_vector)

    middle_vector = np.array([0,0,0])
    self.segment_vectors = []
    self.clip_plane_normals = []
    for (ix, vertex) in enumerate(vertices):
      next_vertex_ix = ix + 1 if ix < len(vertices) - 1 else 0
      next_vertex = vertices[next_vertex_ix]
      self.segment_vectors.append(
        normalize_vector(np.subtract(next_vertex, vertex), segment_vector_mag),
      )
      self.clip_plane_normals.append(np.cross(vertex, next_vertex))
      middle_vector = np.add(
        middle_vector,
        np.array(vertex) / len(vertices)
      )

    self.normal_vector = normalize_vector(
      np.cross(
        self.segment_vectors[0],
        self.segment_vectors[1]
      ),
      segment_vector_mag
    )

    self.v_vector = normalize_vector(
      np.cross(self.normal_vector, self.u_vector),
      segment_vector_mag
    )

    self.rotation_angle = 360 / face_generator_definition.num_segments

  def _vector_outside_clip_bounds(self, vector: np.ndarray):
    for (plane_ix, plane_normal) in enumerate(self.clip_plane_normals):
      # Equation of a plane: Ax + By + Cz + D = 0
      res = np.sum([plane_normal[ix] * vector[ix] for ix in range(3)])
      if res > 0:
        return plane_ix
    return None

  def sink_vector(self, vector, sink_depth: float):
    sink_multiplier = (FACE_NORMAL_DISTANCE - sink_depth) / FACE_NORMAL_DISTANCE;
    return vector * sink_multiplier

  def uv_coordinates_to_face_coordinates(self, uv_coordinates: UV, sink_depth=0):
    local_vector = np.add(
      np.multiply(uv_coordinates[0], self.u_vector),
      np.multiply(uv_coordinates[1], self.v_vector)
    )
    local_vector = np.add(self.origin_vector, local_vector)

    if sink_depth != 0:
      local_vector = self.sink_vector(local_vector, sink_depth)

    return local_vector


class Face(Renderable):

  def __init__(self,
    face_vertices: tuple[Vertex, Vertex, Vertex],
    puzzle_face: PuzzleFace,
    ctx: moderngl.Context,
    texture_location: int,
    texture_uvs: tuple[UV, UV, UV],
    ):
    self.face_vertices = face_vertices
    self.vertex_uvs = texture_uvs # Not Used, but don't want to hurt its feelings

    self.coordinate_system = FaceCoordinateSystem(
      puzzle_face.generator_definition, face_vertices
    )
    self.puzzle_face = puzzle_face

    self.line_color = DEFAULT_LINE_COLOR

    self.matrix = glm.mat4()

    (terrain_vertices, terrain_uvs) = self.__make_terrain_vertices()
    self.terrain_shader = get_shader_program(ctx, "image")
    self.terrain_shader['u_texture_0'] = texture_location
    self.terrain_buffer = self.__make_vbo_with_uv(ctx, terrain_vertices, terrain_uvs)
    self.terrain_vertex_array = self.__make_vao(
      ctx,
      self.terrain_shader,
      [(self.terrain_buffer, "2f 3f", "in_textcoord_0", "in_position")]
    )

    [carve_vertices, wall_vertices] = self.__make_carve_vertices()
    self.carve_shader = get_shader_program(ctx, "line")
    self.carve_buffer = self.__make_vbo(ctx, carve_vertices)
    self.carve_vertex_array = self.__make_vao(
      ctx,
      self.carve_shader,
      [(self.carve_buffer, "3f", "in_position")]
    )

    self.wall_shader = get_shader_program(ctx, "line")
    self.wall_shader['v_color'] = WALL_COLOR
    self.wall_buffer = self.__make_vbo(ctx, wall_vertices)
    self.wall_vertex_array = self.__make_vao(
      ctx,
      self.wall_shader,
      [(self.wall_buffer, "3f", "in_position")]
    )

    self.nv = glm.vec3(self.coordinate_system.normal_vector)
    self.rotation_animator = Animator(
      lerper=AnimationLerper(
        AnimationLerpFunction.ease_in_out,
        ROTATION_DURATION,
      ),
      start_value=0,
      on_frame=self.__animate_rotate,
      on_stop=self.__stop_rotation
    )

    self.resonance_animator = Animator(
      lerper=AnimationLerper(
        AnimationLerpFunction.linear,
        LUMINATION_DURATION,
      ),
      start_value=LINE_LUMINOSITY_INACTIVE,
      on_frame=self.__animate_resonance,
      on_stop=self.__animate_resonance,
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
        polygon_vertices.append(self.coordinate_system.uv_coordinates_to_face_coordinates(node.uv_coordinates))
        polygon_uvs.append(node.uv_coordinates)
    # Render underside triangles
    # TODO: Figure out how to commute the carving depth into the underside faces
    # for (ix, vertex) in enumerate(self.face_vertices):
    #   polygon_vertices.extend([
    #     vertex,
    #     self.face_vertices[ix+1 if ix != 2 else 0],
    #     [0,0,0],
    #   ])
    #   polygon_uvs.extend([(0,0),(1,1),(0.5, SIN60)])

    return (polygon_vertices, polygon_uvs)

  def __make_carve_vertices(self):
    polygons = self.puzzle_face.active_polygons
    active_polygon_vertices = []
    wall_vertices = []
    for polygon in polygons:
      # basin
      for node in polygon.nodes:
        active_polygon_vertices.append(
          self.coordinate_system.uv_coordinates_to_face_coordinates(node.uv_coordinates, CARVE_DEPTH)
        )

      # walls
      inactive_neighbor_lines = polygon.get_inactive_neighbor_lines()
      for inactive_line_nodes in inactive_neighbor_lines:
        terrain_coordinates = [
          self.coordinate_system.uv_coordinates_to_face_coordinates(node.uv_coordinates)
          for node in inactive_line_nodes
        ]
        carve_coordinates = [
          self.coordinate_system.sink_vector(coordinates, CARVE_DEPTH)
          for coordinates in terrain_coordinates
        ]
        quad_triangles = [
          terrain_coordinates[0],terrain_coordinates[1],carve_coordinates[0],
          carve_coordinates[1], carve_coordinates[0], terrain_coordinates[1]
        ]
        wall_vertices.extend([v for v in quad_triangles])

    return (active_polygon_vertices, wall_vertices)

  def __make_vao(self, ctx, shader, context):
    return ctx.vertex_array(shader, context)

  def __make_vbo(self, ctx, vertices):
    return ctx.buffer(np.array(vertices, dtype='f4'))

  def __make_vbo_with_uv(self, ctx, vertices, uvs):
    return self.__make_vbo(ctx, merge_collection_items(uvs, vertices))

  def __rotate_by_degrees(self, degrees):
    self.matrix = glm.rotate(glm.mat4(), glm.radians(degrees), self.nv)

  def __stop_rotation(self, rotation_angle):
    self.__rotate_by_degrees(rotation_angle)
    self.puzzle_face.rotate()
    emit_event(FACE_ROTATED, {})

  def __animate_rotate(self, rotation_angle: float):
    self.__rotate_by_degrees(rotation_angle)

  def renderFace(self, camera: Camera, model_matrix, delta_time):
      m_mvp = camera.view_projection_matrix() * model_matrix * self.matrix
      self.terrain_shader["m_mvp"].write(m_mvp)
      self.terrain_vertex_array.render()
      self.carve_shader["v_color"].write(self.line_color)
      self.carve_shader["m_mvp"].write(m_mvp)
      self.carve_vertex_array.render()
      self.wall_shader["m_mvp"].write(m_mvp)
      self.wall_vertex_array.render()

      self.rotation_animator.frame(delta_time)
      self.resonance_animator.frame(delta_time)

  def rotate(self):
    self.rotation_animator.start(
      self.rotation_animator.current_value + self.coordinate_system.rotation_angle
    )

  def set_is_resonant(self, is_resonant: bool):
    self.resonance_animator.start(
      LINE_LUMINOSITY_ACTIVE if is_resonant else LINE_LUMINOSITY_INACTIVE
    )

  def __animate_resonance(self, new_value: float):
    self.line_color = BASE_LINE_COLOR * new_value

  def destroy(self):
      self.terrain_buffer.release()
      self.carve_buffer.release()
      self.wall_buffer.release()
      self.terrain_shader.release()
      self.carve_shader.release()
      self.wall_shader.release()
      self.terrain_vertex_array.release()
      self.carve_vertex_array.release()
      self.wall_vertex_array.release()

  def projected_vertices(self, matrix) -> list[glm.vec4]:
    # This returns a vec4 in clip space
    return [matrix * self.matrix * glm.vec4(vertex, 1.0) for vertex in self.face_vertices]