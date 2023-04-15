import glm

from engine.animation import Animator, AnimationLerper, AnimationLerpFunction
from ui.image_plane import ImagePlane

DISPLACE = 0.001

class NextButton(ImagePlane):
    def __init__( self, ctx, camera_matrix, position, **kwargs):
        super().__init__(
            ctx, camera_matrix,
            position, glm.vec2(0.08, 0.08),
            "next_button.png", **kwargs)
        
        self.matrix = self.matrix * glm.rotate(
            glm.radians(-90), glm.vec3(0, 0, 1))
        self.animate_matrix = glm.mat4()
        self.position_animator = Animator(
            AnimationLerper(AnimationLerpFunction.ease_in_out, 1000),
            start_value=-DISPLACE,
            on_stop=self._reverse_animator,
        )
        self.position_animator.start(DISPLACE)
    
    def _reverse_animator(self, old_target):
        new_target = -DISPLACE if old_target == DISPLACE else DISPLACE
        self.position_animator.start(new_target)
    
    def render(self, delta_time: int, opacity=1.0):
        y = self.position_animator.frame(delta_time)
        self.animate_matrix  = self.animate_matrix * glm.translate(glm.vec3(0, y, 0))
        matrix = self.animate_matrix * self.matrix
        self.obj.shader["m_mvp"].write(matrix)
        super().render(delta_time)